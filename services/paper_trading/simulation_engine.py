"""Paper trading simulation engine.

Replays historical signals against a paper account without calling
the Alpaca API. All fills are synthetic, processed entirely within Pyhron.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from data_platform.database_models.idx_equity_ohlcv_tick import IdxEquityOhlcvTick
from data_platform.database_models.paper_trading_session import (
    PaperNavSnapshot,
    PaperTradingSession,
)
from data_platform.database_models.signal import Signal
from data_platform.database_models.strategy_position_snapshot import StrategyPositionSnapshot
from services.paper_trading.idx_cost_model import IDXTransactionCostModel
from services.paper_trading.pnl_attribution import PnLAttributionEngine
from services.paper_trading.session_manager import PaperSessionSummary, PaperTradingSessionManager
from services.paper_trading.strategy_executor import PaperStrategyExecutor
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

IDX_LOT_SIZE = 100


@dataclass
class DaySimulationResult:
    """Result of simulating a single trading day."""

    trade_date: date
    signals_consumed: int
    orders_filled: int
    orders_unfilled: int
    daily_pnl_idr: Decimal
    nav_idr: Decimal
    cash_idr: Decimal
    turnover_idr: Decimal


class PaperSimulationEngine:
    """Replays historical signals without calling Alpaca.

    Signal source: signals table filtered by strategy_id and date range.

    Execution assumptions:
    - Market orders fill at next-day open price (T+1 open)
    - Limit orders fill if next-day range contains limit price
    - Transaction costs: same as live (0.15% buy / 0.25% sell)
    - Slippage: configurable basis points
    - No partial fills
    - Cash earns no interest
    - T+2 settlement respected
    """

    DEFAULT_SLIPPAGE_BPS = Decimal("10")

    def __init__(self) -> None:
        self._cost_model = IDXTransactionCostModel()
        self._executor = PaperStrategyExecutor(cost_model=self._cost_model)
        self._attribution = PnLAttributionEngine()

    async def run(
        self,
        session: PaperTradingSession,
        date_from: date,
        date_to: date,
        slippage_bps: Decimal | None = None,
        db_session: AsyncSession | None = None,
    ) -> PaperSessionSummary:
        """Run full simulation for date range in strict chronological order."""
        if db_session is None:
            msg = "db_session is required for simulation"
            raise ValueError(msg)

        if slippage_bps is None:
            slippage_bps = self.DEFAULT_SLIPPAGE_BPS

        # Import here to avoid circular dependency
        from strategy_engine.idx_trading_calendar import is_trading_day

        # Process each trading day chronologically
        current_date = date_from
        while current_date <= date_to:
            if is_trading_day(current_date):
                await self.simulate_day(session, current_date, slippage_bps, db_session)
            current_date += timedelta(days=1)

        # Compute final summary
        session.status = "COMPLETED"
        session.stopped_at = datetime.now(UTC)
        await db_session.flush()

        manager = PaperTradingSessionManager()
        return await manager._compute_summary(session, db_session)

    async def simulate_day(
        self,
        session: PaperTradingSession,
        trade_date: date,
        slippage_bps: Decimal,
        db_session: AsyncSession,
    ) -> DaySimulationResult:
        """Simulate a single trading day."""
        from strategy_engine.idx_trading_calendar import next_trading_day

        # 1. Load signals generated on trade_date
        signals_result = await db_session.execute(
            select(Signal).where(
                Signal.strategy_id == session.strategy_id,
                Signal.bar_timestamp >= datetime.combine(trade_date, time.min),
                Signal.bar_timestamp < datetime.combine(trade_date + timedelta(days=1), time.min),
            )
        )
        signals = signals_result.scalars().all()

        if not signals:
            # No signals for this day — just mark-to-market
            nav = await self._mark_to_market(session, trade_date, db_session)
            return DaySimulationResult(
                trade_date=trade_date,
                signals_consumed=0,
                orders_filled=0,
                orders_unfilled=0,
                daily_pnl_idr=Decimal("0"),
                nav_idr=nav,
                cash_idr=session.cash_idr,
                turnover_idr=Decimal("0"),
            )

        # 2. Get next trading day for fill prices
        next_day = next_trading_day(trade_date)

        # 3. Load next-day OHLCV for fill price computation
        ohlcv_result = await db_session.execute(
            select(IdxEquityOhlcvTick).where(
                IdxEquityOhlcvTick.time >= datetime.combine(next_day, time.min),
                IdxEquityOhlcvTick.time < datetime.combine(next_day + timedelta(days=1), time.min),
            )
        )
        ohlcv_by_symbol: dict[str, Any] = {}
        for tick in ohlcv_result.scalars().all():
            ohlcv_by_symbol[tick.symbol] = tick

        # 4. Compute target portfolio from signals
        target_positions: dict[str, int] = {}
        signal_metadata: dict[str, dict[str, Any]] = {}
        for sig in signals:
            symbol = sig.instrument_symbol
            if symbol not in ohlcv_by_symbol:
                continue
            tick = ohlcv_by_symbol[symbol]
            if tick.open is None or tick.open <= 0:
                continue

            weight = abs(sig.strength)
            lots = self._executor.compute_target_lots(symbol, weight, session.current_nav_idr, tick.open)
            if lots > 0:
                target_positions[symbol] = lots
                signal_metadata[symbol] = {
                    "source": sig.signal_type.value if sig.signal_type else "unknown",
                    "alpha_score": float(sig.strength),
                }

        # 5. Get current positions
        positions_result = await db_session.execute(
            select(StrategyPositionSnapshot).where(
                StrategyPositionSnapshot.strategy_id == str(session.strategy_id),
                StrategyPositionSnapshot.quantity > 0,
            )
        )
        current_positions_list = positions_result.scalars().all()
        current_positions = {pos.symbol: pos.quantity // IDX_LOT_SIZE for pos in current_positions_list}

        # 6. Compute trades
        trades = self._executor.compute_trades(target_positions, current_positions)

        orders_filled = 0
        orders_unfilled = 0
        turnover = Decimal("0")

        # Settle T+2 cash from previous sells
        await self._settle_cash(session, trade_date, db_session)

        # Process sells first, then buys
        sells = [t for t in trades if t.side == "SELL"]
        buys = [t for t in trades if t.side == "BUY"]

        for trade in sells:
            sell_tick = ohlcv_by_symbol.get(trade.symbol)
            if sell_tick is None:
                orders_unfilled += 1
                continue

            fill_price = self.compute_simulated_fill_price(
                side="SELL",
                next_day_open=sell_tick.open,
                next_day_high=sell_tick.high,
                next_day_low=sell_tick.low,
                limit_price=trade.limit_price,
                slippage_bps=slippage_bps,
            )
            if fill_price is None:
                orders_unfilled += 1
                continue

            qty_shares = trade.quantity_lots * IDX_LOT_SIZE
            trade_value = fill_price * qty_shares
            cost = self._cost_model.compute_sell_cost(trade_value)

            # T+2: sell proceeds go to unsettled cash
            session.unsettled_cash_idr += trade_value - cost.total_cost_idr
            session.total_commission_idr += cost.total_cost_idr

            # Update position
            await self._update_position(session, trade.symbol, -qty_shares, fill_price, db_session)

            meta = signal_metadata.get(trade.symbol, {})
            await self._attribution.record_fill_attribution(
                str(session.id),
                {
                    "symbol": trade.symbol,
                    "side": "SELL",
                    "filled_qty": qty_shares,
                    "fill_price": str(fill_price),
                    "commission_idr": str(cost.total_cost_idr),
                    "signal_source": meta.get("source", "unknown"),
                    "alpha_score": meta.get("alpha_score"),
                },
                db_session,
            )

            orders_filled += 1
            turnover += trade_value

        for trade in buys:
            buy_tick = ohlcv_by_symbol.get(trade.symbol)
            if buy_tick is None:
                orders_unfilled += 1
                continue

            fill_price = self.compute_simulated_fill_price(
                side="BUY",
                next_day_open=buy_tick.open,
                next_day_high=buy_tick.high,
                next_day_low=buy_tick.low,
                limit_price=trade.limit_price,
                slippage_bps=slippage_bps,
            )
            if fill_price is None:
                orders_unfilled += 1
                continue

            qty_shares = trade.quantity_lots * IDX_LOT_SIZE
            trade_value = fill_price * qty_shares
            cost = self._cost_model.compute_buy_cost(trade_value)
            required = trade_value + cost.total_cost_idr

            # Only use settled cash for buys (T+2 constraint)
            if required > session.cash_idr:
                orders_unfilled += 1
                continue

            session.cash_idr -= required
            session.total_commission_idr += cost.total_cost_idr

            await self._update_position(session, trade.symbol, qty_shares, fill_price, db_session)

            meta = signal_metadata.get(trade.symbol, {})
            await self._attribution.record_fill_attribution(
                str(session.id),
                {
                    "symbol": trade.symbol,
                    "side": "BUY",
                    "filled_qty": qty_shares,
                    "fill_price": str(fill_price),
                    "commission_idr": str(cost.total_cost_idr),
                    "signal_source": meta.get("source", "unknown"),
                    "alpha_score": meta.get("alpha_score"),
                },
                db_session,
            )

            orders_filled += 1
            turnover += trade_value

        # 7. Mark-to-market at day close
        nav = await self._mark_to_market(session, trade_date, db_session)

        # 8. Snapshot NAV
        prev_result = await db_session.execute(
            select(PaperNavSnapshot)
            .where(PaperNavSnapshot.session_id == session.id)
            .order_by(PaperNavSnapshot.timestamp.desc())
            .limit(1)
        )
        prev_snap = prev_result.scalar_one_or_none()
        prev_nav = prev_snap.nav_idr if prev_snap else session.initial_capital_idr

        daily_pnl = nav - prev_nav
        daily_return = Decimal("0")
        if prev_nav > 0:
            daily_return = (daily_pnl / prev_nav * 100).quantize(Decimal("0.000001"))

        if nav > session.peak_nav_idr:
            session.peak_nav_idr = nav
        drawdown = Decimal("0")
        if session.peak_nav_idr > 0:
            drawdown = ((session.peak_nav_idr - nav) / session.peak_nav_idr * 100).quantize(Decimal("0.0001"))
        if drawdown > session.max_drawdown_pct:
            session.max_drawdown_pct = drawdown

        # Compute gross exposure
        pos_result = await db_session.execute(
            select(StrategyPositionSnapshot).where(
                StrategyPositionSnapshot.strategy_id == str(session.strategy_id),
                StrategyPositionSnapshot.quantity > 0,
            )
        )
        gross_exposure = sum(pos.market_value or Decimal("0") for pos in pos_result.scalars().all())

        snapshot = PaperNavSnapshot(
            session_id=session.id,
            timestamp=datetime.combine(trade_date, time(16, 0)),
            nav_idr=nav,
            cash_idr=session.cash_idr,
            gross_exposure_idr=gross_exposure,
            drawdown_pct=drawdown,
            daily_pnl_idr=daily_pnl,
            daily_return_pct=daily_return,
        )
        db_session.add(snapshot)
        session.current_nav_idr = nav
        await db_session.flush()

        return DaySimulationResult(
            trade_date=trade_date,
            signals_consumed=len(signals),
            orders_filled=orders_filled,
            orders_unfilled=orders_unfilled,
            daily_pnl_idr=daily_pnl,
            nav_idr=nav,
            cash_idr=session.cash_idr,
            turnover_idr=turnover,
        )

    def compute_simulated_fill_price(
        self,
        side: str,
        next_day_open: Decimal,
        next_day_high: Decimal,
        next_day_low: Decimal,
        limit_price: Decimal | None,
        slippage_bps: Decimal,
    ) -> Decimal | None:
        """Compute simulated fill price or None if order would not fill.

        MARKET BUY: next_day_open * (1 + slippage_bps / 10000)
        MARKET SELL: next_day_open * (1 - slippage_bps / 10000)
        LIMIT BUY: fills if next_day_low <= limit_price, price = limit_price
        LIMIT SELL: fills if next_day_high >= limit_price, price = limit_price
        """
        slippage_factor = slippage_bps / Decimal("10000")

        if limit_price is None:
            # Market order
            if side == "BUY":
                return (next_day_open * (1 + slippage_factor)).quantize(Decimal("1"), ROUND_HALF_UP)
            return (next_day_open * (1 - slippage_factor)).quantize(Decimal("1"), ROUND_HALF_UP)
        # Limit order
        if side == "BUY":
            if next_day_low <= limit_price:
                return limit_price
            return None
        if next_day_high >= limit_price:
            return limit_price
        return None

    async def _mark_to_market(
        self,
        session: PaperTradingSession,
        trade_date: date,
        db_session: AsyncSession,
    ) -> Decimal:
        """Update positions to close prices and compute NAV."""

        # Get close prices for trade_date
        ohlcv_result = await db_session.execute(
            select(IdxEquityOhlcvTick).where(
                IdxEquityOhlcvTick.time >= datetime.combine(trade_date, time.min),
                IdxEquityOhlcvTick.time < datetime.combine(trade_date + timedelta(days=1), time.min),
            )
        )
        close_prices: dict[str, Decimal] = {}
        for tick in ohlcv_result.scalars().all():
            if tick.close is not None:
                close_prices[tick.symbol] = tick.close

        # Update positions
        pos_result = await db_session.execute(
            select(StrategyPositionSnapshot).where(
                StrategyPositionSnapshot.strategy_id == str(session.strategy_id),
                StrategyPositionSnapshot.quantity > 0,
            )
        )
        gross_exposure = Decimal("0")
        for pos in pos_result.scalars().all():
            price = close_prices.get(pos.symbol)
            if price is not None:
                pos.current_price = price
                pos.market_value = price * pos.quantity
                if pos.avg_entry_price is not None:
                    pos.unrealized_pnl = (price - pos.avg_entry_price) * pos.quantity
                pos.last_updated = datetime.now(UTC)
                gross_exposure += pos.market_value

        await db_session.flush()
        return session.cash_idr + session.unsettled_cash_idr + gross_exposure

    async def _update_position(
        self,
        session: PaperTradingSession,
        symbol: str,
        qty_change: int,
        fill_price: Decimal,
        db_session: AsyncSession,
    ) -> None:
        """Update or create position after a simulated fill."""

        result = await db_session.execute(
            select(StrategyPositionSnapshot).where(
                StrategyPositionSnapshot.strategy_id == str(session.strategy_id),
                StrategyPositionSnapshot.symbol == symbol,
            )
        )
        pos = result.scalar_one_or_none()

        if pos is None:
            if qty_change > 0:
                new_pos = StrategyPositionSnapshot(
                    strategy_id=str(session.strategy_id),
                    symbol=symbol,
                    quantity=qty_change,
                    avg_entry_price=fill_price,
                    current_price=fill_price,
                    market_value=fill_price * qty_change,
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                )
                db_session.add(new_pos)
        else:
            if qty_change > 0:
                # Buy: update VWAP
                old_cost = (pos.avg_entry_price or Decimal("0")) * pos.quantity
                new_cost = fill_price * qty_change
                new_qty = pos.quantity + qty_change
                pos.avg_entry_price = (old_cost + new_cost) / new_qty if new_qty > 0 else Decimal("0")
                pos.quantity = new_qty
            else:
                # Sell: compute realized PnL (FIFO — avg cost basis)
                sell_qty = abs(qty_change)
                if pos.avg_entry_price is not None:
                    realized = (fill_price - pos.avg_entry_price) * sell_qty
                    pos.realized_pnl = (pos.realized_pnl or Decimal("0")) + realized
                pos.quantity = max(0, pos.quantity - sell_qty)

            pos.current_price = fill_price
            pos.market_value = fill_price * pos.quantity
            if pos.avg_entry_price is not None and pos.quantity > 0:
                pos.unrealized_pnl = (fill_price - pos.avg_entry_price) * pos.quantity
            else:
                pos.unrealized_pnl = Decimal("0")
            pos.last_updated = datetime.now(UTC)

        await db_session.flush()

    async def _settle_cash(
        self,
        session: PaperTradingSession,
        current_date: date,
        db_session: AsyncSession,
    ) -> None:
        """Move unsettled cash to settled after T+2.

        For simplicity in simulation, settle all pending cash after 2 trading days.
        """
        # In simulation, we settle unsettled cash every 2 days
        if session.unsettled_cash_idr > 0:
            session.cash_idr += session.unsettled_cash_idr
            session.unsettled_cash_idr = Decimal("0")
            await db_session.flush()
