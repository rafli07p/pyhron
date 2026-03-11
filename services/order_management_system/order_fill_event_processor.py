"""Order fill event processor for the Pyhron OMS.

Processes broker fill callbacks, accumulates partial fills, computes
volume-weighted average prices, transitions orders through the state
machine, writes trade execution logs, and updates positions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from data_platform.database_models.strategy_position_snapshot import (
    StrategyPositionSnapshot,
)
from data_platform.database_models.strategy_trade_execution_log import (
    StrategyTradeExecutionLog,
    TradeSideEnum,
)
from data_platform.models.trading import Order, OrderStatusEnum
from services.order_management_system.order_state_machine import OrderStateMachine
from shared.async_database_session import get_session
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from shared.kafka_producer_consumer import PyhronProducer

logger = get_logger(__name__)


# ── IDX T+2 Settlement ──────────────────────────────────────────────────────

IDX_MARKET_HOLIDAYS_2025 = [
    date(2025, 1, 1),   # New Year
    date(2025, 1, 27),  # Isra Mi'raj
    date(2025, 1, 29),  # Chinese New Year
    date(2025, 3, 29),  # Nyepi
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 1),   # Labour Day
    date(2025, 5, 12),  # Eid al-Fitr
    date(2025, 5, 29),  # Ascension Day
    date(2025, 6, 1),   # Pancasila Day
    date(2025, 6, 6),   # Eid al-Adha
    date(2025, 6, 27),  # Islamic New Year
    date(2025, 8, 17),  # Independence Day
    date(2025, 9, 5),   # Prophet's Birthday
    date(2025, 12, 25), # Christmas
]


def calculate_settlement_date(trade_date: date) -> date:
    """IDX T+2: count 2 business days excluding weekends and market holidays."""
    settlement = trade_date
    business_days_added = 0
    while business_days_added < 2:
        settlement += timedelta(days=1)
        if settlement.weekday() < 5 and settlement not in IDX_MARKET_HOLIDAYS_2025:
            business_days_added += 1
    return settlement


# ── Fill Event ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FillEvent:
    """A broker fill event to be processed.

    Attributes:
        client_order_id: The client-assigned order identifier.
        broker_order_id: The broker-assigned order identifier.
        fill_id: Unique fill identifier for idempotent processing.
        filled_quantity: Number of shares filled in this execution.
        filled_price: Execution price for this fill.
        commission: Broker commission for this fill.
        tax: Tax charged on this fill (e.g. IDX transaction tax).
        event_type: Fill event type ("fill" or "partial_fill").
        timestamp: ISO timestamp of the fill event from the broker.
    """

    client_order_id: str
    broker_order_id: str
    filled_quantity: int
    filled_price: float
    commission: float = 0.0
    tax: float = 0.0
    event_type: str = "fill"
    timestamp: str = ""
    fill_id: str = ""


class OrderFillEventProcessor:
    """Processes broker fill callbacks and manages fill accumulation.

    Handles both partial and complete fills by:
      1. Looking up the order in the database (SELECT FOR UPDATE).
      2. Checking fill_id dedup in StrategyTradeExecutionLog.
      3. Computing cumulative filled quantity and VWAP.
      4. Determining the target status (PARTIAL_FILL or FILLED).
      5. Executing the state transition via the OrderStateMachine.
      6. Writing StrategyTradeExecutionLog (immutable).
      7. Updating StrategyPositionSnapshot via upsert.
      8. Calculating T+2 settlement date.
    """

    def __init__(self, producer: PyhronProducer) -> None:
        """Initialize with a Kafka producer for the state machine.

        Args:
            producer: The PyhronProducer for publishing order events.
        """
        self._state_machine = OrderStateMachine(producer)
        self._producer = producer

    async def process_fill(self, fill: FillEvent) -> bool:
        """Process a single fill event from the broker.

        Accumulates the fill quantity, computes VWAP, transitions the
        order, writes a trade execution log, and updates the position.
        Idempotent: duplicate fill_ids are detected and skipped.

        Args:
            fill: The FillEvent to process.

        Returns:
            True if the fill was successfully processed, False if the
            order was not found or could not be transitioned.
        """
        async with get_session() as session:
            # Step 1: Fetch order with SELECT FOR UPDATE for concurrency safety
            result = await session.execute(
                select(Order)
                .where(Order.client_order_id == fill.client_order_id)
                .with_for_update()
            )
            order = result.scalar_one_or_none()

            if order is None:
                logger.error(
                    "fill_for_unknown_order",
                    client_order_id=fill.client_order_id,
                    broker_order_id=fill.broker_order_id,
                )
                return False

            # Validate that the order is in a state that accepts fills
            if order.status not in (
                OrderStatusEnum.ACKNOWLEDGED,
                OrderStatusEnum.PARTIAL_FILL,
                OrderStatusEnum.SUBMITTED,
            ):
                logger.warning(
                    "fill_for_order_in_unexpected_state",
                    client_order_id=fill.client_order_id,
                    current_status=order.status.value,
                )
                return False

            # Step 2: Dedup check — skip if fill_id already recorded
            fill_id = fill.fill_id or str(uuid.uuid4())
            if fill.fill_id:
                existing_trade = await session.execute(
                    select(StrategyTradeExecutionLog).where(
                        StrategyTradeExecutionLog.broker_trade_id == fill.fill_id
                    )
                )
                if existing_trade.scalar_one_or_none() is not None:
                    logger.warning(
                        "duplicate_fill_skipped",
                        fill_id=fill.fill_id,
                        client_order_id=fill.client_order_id,
                    )
                    return False

        # Step 3: Accumulate fills and compute VWAP
        current_filled: int = order.filled_quantity or 0
        cumulative_filled: int = current_filled + fill.filled_quantity

        current_avg = Decimal(str(order.avg_fill_price)) if order.avg_fill_price else Decimal("0")
        filled_price = Decimal(str(fill.filled_price))
        filled_quantity = Decimal(str(fill.filled_quantity))
        current_filled_dec = Decimal(str(current_filled))
        cumulative_filled_dec = Decimal(str(cumulative_filled))
        if cumulative_filled > 0:
            new_avg_price_dec = (
                (current_avg * current_filled_dec) + (filled_price * filled_quantity)
            ) / cumulative_filled_dec
        else:
            new_avg_price_dec = filled_price
        new_avg_price: float = float(new_avg_price_dec)

        # Step 4: Determine target status
        is_full_fill = cumulative_filled >= order.quantity
        target_status = OrderStatusEnum.FILLED if is_full_fill else OrderStatusEnum.PARTIAL_FILL

        # Step 5: Calculate T+2 settlement date
        trade_date = datetime.now(tz=UTC).date()
        if fill.timestamp:
            try:
                trade_date = datetime.fromisoformat(fill.timestamp).date()
            except (ValueError, TypeError):
                pass
        settlement = calculate_settlement_date(trade_date)

        # Step 6: State transition
        event_data: dict[str, object] = {
            "filled_quantity": cumulative_filled,
            "filled_price": fill.filled_price,
            "avg_fill_price": new_avg_price,
            "commission": fill.commission,
            "tax": fill.tax,
            "broker_order_id": fill.broker_order_id,
        }

        await self._state_machine.transition(
            order=order,
            to_status=target_status,
            event_data=event_data,
            source="broker_fill",
        )

        # Step 7: Write StrategyTradeExecutionLog (immutable, idempotent via fill_id)
        trade_side = TradeSideEnum.BUY if order.side == "buy" else TradeSideEnum.SELL
        async with get_session() as session:
            trade_log = StrategyTradeExecutionLog(
                id=uuid.uuid4(),
                client_order_id=fill.client_order_id,
                broker_trade_id=fill_id,
                symbol=order.symbol,
                exchange=order.exchange,
                side=trade_side,
                quantity=fill.filled_quantity,
                price=Decimal(str(fill.filled_price)),
                commission=Decimal(str(fill.commission)),
                tax=Decimal(str(fill.tax)),
                trade_time=datetime.now(tz=UTC),
                settlement_date=settlement,
            )
            session.add(trade_log)
            await session.commit()

        # Step 8: Update position via upsert
        await self._upsert_position(
            order=order,
            fill=fill,
            filled_price_dec=filled_price,
        )

        logger.info(
            "fill_processed",
            client_order_id=fill.client_order_id,
            broker_order_id=fill.broker_order_id,
            fill_id=fill_id,
            this_fill_qty=fill.filled_quantity,
            this_fill_price=fill.filled_price,
            cumulative_filled=cumulative_filled,
            total_quantity=order.quantity,
            vwap=round(new_avg_price, 4),
            status=target_status.value,
            settlement_date=settlement.isoformat(),
            is_full_fill=is_full_fill,
        )

        return True

    async def _upsert_position(
        self,
        order: Order,
        fill: FillEvent,
        filled_price_dec: Decimal,
    ) -> None:
        """Update position using INSERT ... ON CONFLICT DO UPDATE.

        BUY fills increase quantity and recalculate avg_cost (VWAP).
        SELL fills decrease quantity and calculate realized_pnl.
        """
        strategy_id = order.strategy_id
        symbol = order.symbol
        exchange = order.exchange or "IDX"
        is_buy = order.side == "buy"
        fill_qty = fill.filled_quantity
        now = datetime.now(tz=UTC)

        async with get_session() as session:
            # Fetch current position for VWAP / realized PnL calculation
            result = await session.execute(
                select(StrategyPositionSnapshot).where(
                    StrategyPositionSnapshot.strategy_id == strategy_id,
                    StrategyPositionSnapshot.symbol == symbol,
                ).with_for_update()
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                # No position yet — insert
                new_pos = StrategyPositionSnapshot(
                    id=uuid.uuid4(),
                    strategy_id=strategy_id,
                    symbol=symbol,
                    exchange=exchange,
                    quantity=fill_qty if is_buy else 0,
                    avg_entry_price=filled_price_dec if is_buy else None,
                    current_price=filled_price_dec,
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    market_value=filled_price_dec * Decimal(str(fill_qty)) if is_buy else Decimal("0"),
                    last_updated=now,
                )
                session.add(new_pos)
            else:
                # Update existing position
                current_qty = existing.quantity or 0
                current_avg = existing.avg_entry_price or Decimal("0")
                current_realized = existing.realized_pnl or Decimal("0")

                if is_buy:
                    # Increase quantity, recalculate VWAP
                    new_qty = current_qty + fill_qty
                    if new_qty > 0:
                        new_avg = (
                            current_avg * Decimal(str(current_qty))
                            + filled_price_dec * Decimal(str(fill_qty))
                        ) / Decimal(str(new_qty))
                    else:
                        new_avg = filled_price_dec
                    existing.quantity = new_qty
                    existing.avg_entry_price = new_avg
                else:
                    # Decrease quantity, calculate realized PnL
                    # realized_pnl = (fill_price - avg_cost) × qty_sold
                    # (quantity stored in shares, not lots)
                    realized_delta = (filled_price_dec - current_avg) * Decimal(str(fill_qty))
                    new_qty = max(0, current_qty - fill_qty)
                    existing.quantity = new_qty
                    existing.realized_pnl = current_realized + realized_delta

                existing.current_price = filled_price_dec
                existing.market_value = filled_price_dec * Decimal(str(existing.quantity))
                if existing.avg_entry_price and existing.quantity > 0:
                    existing.unrealized_pnl = (
                        (filled_price_dec - existing.avg_entry_price)
                        * Decimal(str(existing.quantity))
                    )
                else:
                    existing.unrealized_pnl = Decimal("0")
                existing.last_updated = now

            await session.commit()

        logger.info(
            "position_updated",
            strategy_id=strategy_id,
            symbol=symbol,
            side="BUY" if is_buy else "SELL",
            fill_qty=fill_qty,
        )

    async def process_fill_batch(self, fills: list[FillEvent]) -> dict[str, int]:
        """Process a batch of fill events.

        Args:
            fills: List of FillEvent instances to process.

        Returns:
            Dict with ``processed`` and ``failed`` counts.
        """
        processed = 0
        failed = 0

        for fill in fills:
            try:
                success = await self.process_fill(fill)
                if success:
                    processed += 1
                else:
                    failed += 1
            except Exception:
                logger.exception(
                    "fill_processing_error",
                    client_order_id=fill.client_order_id,
                )
                failed += 1

        logger.info(
            "fill_batch_complete",
            total=len(fills),
            processed=processed,
            failed=failed,
        )

        return {"processed": processed, "failed": failed}
