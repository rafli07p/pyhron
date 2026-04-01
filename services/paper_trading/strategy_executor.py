"""Paper trading strategy executor.

Consumes strategy signals from Kafka and translates them into orders
submitted through the OMS, respecting IDX lot sizing, T+2 settlement,
and capital constraints.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from data_platform.database_models.pyhron_strategy_position_snapshot import PyhronStrategyPositionSnapshot
from services.paper_trading.idx_cost_model import IDXTransactionCostModel
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from data_platform.database_models.pyhron_paper_trading_session import PyhronPaperTradingSession

logger = get_logger(__name__)

IDX_LOT_SIZE = 100


@dataclass
class TradeInstruction:
    """A single trade to execute."""

    symbol: str
    side: str  # BUY | SELL
    quantity_lots: int
    order_type: str  # MARKET | LIMIT
    limit_price: Decimal | None
    signal_source: str
    alpha_score: Decimal | None


@dataclass
class RebalanceResult:
    """Result of processing a rebalance signal batch."""

    session_id: str
    rebalance_at: datetime
    signals_consumed: int
    orders_submitted: int
    orders_rejected: int
    estimated_turnover_idr: Decimal
    instructions: list[TradeInstruction] = field(default_factory=list)


class PaperStrategyExecutor:
    """Consumes strategy signals and submits orders via the OMS.

    Execution order: sells first (to free capital), then buys.
    Respects T+2 settlement: unsettled cash from sells is not available
    for new buys until T+2.
    """

    MIN_TRADE_VALUE_IDR = Decimal("5_000_000")
    MAX_DAILY_TURNOVER_PCT = Decimal("0.30")

    def __init__(
        self,
        cost_model: IDXTransactionCostModel | None = None,
        order_submitter: Any = None,
    ) -> None:
        self._cost_model = cost_model or IDXTransactionCostModel()
        self._order_submitter = order_submitter

    def compute_target_lots(
        self,
        symbol: str,
        target_weight: Decimal,
        nav_idr: Decimal,
        last_price_idr: Decimal,
    ) -> int:
        """Compute target lots, always flooring to avoid exceeding allocation.

        target_lots = floor((target_weight * nav_idr) / (last_price_idr * 100))
        """
        if last_price_idr <= 0 or nav_idr <= 0:
            return 0
        target_value = target_weight * nav_idr
        lots = target_value / (last_price_idr * IDX_LOT_SIZE)
        return int(lots.to_integral_value(rounding=ROUND_DOWN))

    def compute_trades(
        self,
        target_positions: dict[str, int],
        current_positions: dict[str, int],
    ) -> list[TradeInstruction]:
        """Diff target against current to produce buy/sell instructions.

        Positive delta = buy, negative delta = sell. Zero delta = no action.
        """
        all_symbols = set(target_positions.keys()) | set(current_positions.keys())
        trades: list[TradeInstruction] = []

        for symbol in sorted(all_symbols):
            target = target_positions.get(symbol, 0)
            current = current_positions.get(symbol, 0)
            delta = target - current

            if delta > 0:
                trades.append(
                    TradeInstruction(
                        symbol=symbol,
                        side="BUY",
                        quantity_lots=delta,
                        order_type="MARKET",
                        limit_price=None,
                        signal_source="",
                        alpha_score=None,
                    )
                )
            elif delta < 0:
                trades.append(
                    TradeInstruction(
                        symbol=symbol,
                        side="SELL",
                        quantity_lots=abs(delta),
                        order_type="MARKET",
                        limit_price=None,
                        signal_source="",
                        alpha_score=None,
                    )
                )

        return trades

    async def process_rebalance_signal(
        self,
        session: PyhronPaperTradingSession,
        signals: list[dict[str, Any]],
        last_prices: dict[str, Decimal],
        db_session: AsyncSession,
    ) -> RebalanceResult:
        """Core rebalance logic. Submits sells before buys."""
        nav = session.current_nav_idr
        now = datetime.now(UTC)

        # Compute target positions from signals
        target_positions: dict[str, int] = {}
        signal_metadata: dict[str, dict[str, Any]] = {}
        for sig in signals:
            symbol = sig.get("symbol", "")
            weight = Decimal(str(sig.get("target_weight", "0")))
            price = last_prices.get(symbol, Decimal("0"))
            if price > 0 and weight > 0:
                lots = self.compute_target_lots(symbol, weight, nav, price)
                if lots > 0:
                    target_positions[symbol] = lots
                    signal_metadata[symbol] = {
                        "source": sig.get("signal_source", sig.get("strategy_type", "unknown")),
                        "alpha_score": sig.get("alpha_score"),
                    }

        # Get current positions
        positions_result = await db_session.execute(
            select(PyhronStrategyPositionSnapshot).where(
                PyhronStrategyPositionSnapshot.strategy_id == str(session.strategy_id),
                PyhronStrategyPositionSnapshot.quantity > 0,
            )
        )
        positions = positions_result.scalars().all()
        current_positions = {pos.symbol: pos.quantity // IDX_LOT_SIZE for pos in positions}

        # Compute trades
        raw_trades = self.compute_trades(target_positions, current_positions)

        # Enrich with signal metadata
        for trade in raw_trades:
            meta = signal_metadata.get(trade.symbol, {})
            trade.signal_source = meta.get("source", "unknown")
            alpha = meta.get("alpha_score")
            trade.alpha_score = Decimal(str(alpha)) if alpha is not None else None

        # Apply filters
        filtered_trades = self._apply_trade_filters(raw_trades, last_prices, nav)

        # Separate sells and buys — sells first
        sells = [t for t in filtered_trades if t.side == "SELL"]
        buys = [t for t in filtered_trades if t.side == "BUY"]

        orders_submitted = 0
        orders_rejected = 0
        estimated_turnover = Decimal("0")

        # Submit sells first
        for trade in sells:
            price = last_prices.get(trade.symbol, Decimal("0"))
            trade_value = price * trade.quantity_lots * IDX_LOT_SIZE
            submitted = await self._submit_order(session, trade, db_session)
            if submitted:
                orders_submitted += 1
                estimated_turnover += trade_value
            else:
                orders_rejected += 1

        # Submit buys after
        for trade in buys:
            price = last_prices.get(trade.symbol, Decimal("0"))
            trade_value = price * trade.quantity_lots * IDX_LOT_SIZE
            # Check settled cash is sufficient
            buy_cost = self._cost_model.compute_buy_cost(trade_value)
            required = trade_value + buy_cost.total_cost_idr
            if required > session.cash_idr:
                orders_rejected += 1
                logger.warning(
                    "paper_buy_insufficient_cash",
                    symbol=trade.symbol,
                    required=str(required),
                    available=str(session.cash_idr),
                )
                continue
            submitted = await self._submit_order(session, trade, db_session)
            if submitted:
                orders_submitted += 1
                estimated_turnover += trade_value
            else:
                orders_rejected += 1

        return RebalanceResult(
            session_id=str(session.id),
            rebalance_at=now,
            signals_consumed=len(signals),
            orders_submitted=orders_submitted,
            orders_rejected=orders_rejected,
            estimated_turnover_idr=estimated_turnover,
            instructions=filtered_trades,
        )

    def _apply_trade_filters(
        self,
        trades: list[TradeInstruction],
        last_prices: dict[str, Decimal],
        nav: Decimal,
    ) -> list[TradeInstruction]:
        """Filter out trades below minimum size and cap daily turnover."""
        filtered: list[TradeInstruction] = []
        cumulative_turnover = Decimal("0")
        max_turnover = nav * self.MAX_DAILY_TURNOVER_PCT

        for trade in trades:
            price = last_prices.get(trade.symbol, Decimal("0"))
            trade_value = price * trade.quantity_lots * IDX_LOT_SIZE

            if trade_value < self.MIN_TRADE_VALUE_IDR:
                continue

            if cumulative_turnover + trade_value > max_turnover:
                continue

            cumulative_turnover += trade_value
            filtered.append(trade)

        return filtered

    async def _submit_order(
        self,
        session: PyhronPaperTradingSession,
        instruction: TradeInstruction,
        db_session: AsyncSession,
    ) -> bool:
        """Submit a single order. Returns True on success."""
        if self._order_submitter is None:
            logger.warning("paper_order_no_submitter", symbol=instruction.symbol)
            return False

        try:
            order_data = {
                "client_order_id": str(uuid.uuid4()),
                "symbol": instruction.symbol,
                "side": instruction.side.lower(),
                "order_type": instruction.order_type.lower(),
                "quantity": instruction.quantity_lots * IDX_LOT_SIZE,
                "strategy_id": str(session.strategy_id),
                "session_id": str(session.id),
                "signal_source": instruction.signal_source,
                "alpha_score": str(instruction.alpha_score) if instruction.alpha_score else None,
            }
            if instruction.limit_price is not None:
                order_data["limit_price"] = str(instruction.limit_price)

            await self._order_submitter(order_data)
            return True
        except Exception:
            logger.exception("paper_order_submit_failed", symbol=instruction.symbol)
            return False
