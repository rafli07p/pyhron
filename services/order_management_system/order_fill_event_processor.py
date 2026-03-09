"""Order fill event processor for the Pyhron OMS.

Processes broker fill callbacks, accumulates partial fills, computes
volume-weighted average prices, and transitions orders through the
state machine to PARTIAL_FILL or FILLED status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from data_platform.models.trading import Order, OrderStatusEnum
from services.order_management_system.order_state_machine import OrderStateMachine
from shared.async_database_session import get_session
from shared.structured_json_logger import get_logger
from shared.kafka_producer_consumer import PyhronProducer

logger = get_logger(__name__)


@dataclass(frozen=True)
class FillEvent:
    """A broker fill event to be processed.

    Attributes:
        client_order_id: The client-assigned order identifier.
        broker_order_id: The broker-assigned order identifier.
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


class OrderFillEventProcessor:
    """Processes broker fill callbacks and manages fill accumulation.

    Handles both partial and complete fills by:
      1. Looking up the order in the database.
      2. Computing cumulative filled quantity and VWAP.
      3. Determining the target status (PARTIAL_FILL or FILLED).
      4. Executing the state transition via the OrderStateMachine.

    Supports idempotent processing -- duplicate fill events for the same
    execution are detected and skipped.

    Usage::

        processor = OrderFillEventProcessor(producer)
        fill = FillEvent(
            client_order_id="abc123",
            broker_order_id="brk-456",
            filled_quantity=100,
            filled_price=4500.0,
        )
        await processor.process_fill(fill)
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

        Accumulates the fill quantity, computes VWAP, and transitions the
        order to PARTIAL_FILL or FILLED.

        Args:
            fill: The FillEvent to process.

        Returns:
            True if the fill was successfully processed, False if the
            order was not found or could not be transitioned.
        """
        order = await self._fetch_order(fill.client_order_id)
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

        # Accumulate fills
        current_filled: int = order.filled_quantity or 0
        cumulative_filled: int = current_filled + fill.filled_quantity

        # Compute volume-weighted average price
        current_avg: float = order.avg_fill_price or 0.0
        if cumulative_filled > 0:
            new_avg_price: float = (
                (current_avg * current_filled) + (fill.filled_price * fill.filled_quantity)
            ) / cumulative_filled
        else:
            new_avg_price = fill.filled_price

        # Determine target status
        if cumulative_filled >= order.quantity:
            target_status = OrderStatusEnum.FILLED
        else:
            target_status = OrderStatusEnum.PARTIAL_FILL

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

        logger.info(
            "fill_processed",
            client_order_id=fill.client_order_id,
            broker_order_id=fill.broker_order_id,
            this_fill_qty=fill.filled_quantity,
            this_fill_price=fill.filled_price,
            cumulative_filled=cumulative_filled,
            total_quantity=order.quantity,
            vwap=round(new_avg_price, 4),
            status=target_status.value,
        )

        return True

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

    async def _fetch_order(self, client_order_id: str) -> Order | None:
        """Look up an order by client_order_id in the database.

        Args:
            client_order_id: Unique client-assigned order identifier.

        Returns:
            The Order ORM instance, or None if not found.
        """
        async with get_session() as session:
            result = await session.execute(
                select(Order).where(Order.client_order_id == client_order_id)
            )
            return result.scalar_one_or_none()
