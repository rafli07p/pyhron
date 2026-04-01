"""Order state machine for the Pyhron OMS.

Enforces valid state transitions, persists state changes to the database,
creates immutable OrderEvent records, and publishes events to Kafka.

Transition graph matches proto/orders.proto OrderStatus enum.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

from google.protobuf.timestamp_pb2 import Timestamp
from sqlalchemy import update

from data_platform.database_models.pyhron_order_lifecycle_record import (
    OrderStatusEnum,
)
from data_platform.database_models.pyhron_order_lifecycle_record import (
    PyhronOrderLifecycleRecord as Order,
)
from shared.async_database_session import get_session
from shared.kafka_producer_consumer import PyhronProducer, Topics
from shared.platform_exception_hierarchy import InvalidTransitionError
from shared.proto_generated.equity_orders_pb2 import (
    OrderEvent as OrderEventProto,
)
from shared.proto_generated.equity_orders_pb2 import (
    OrderStatus,
)
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# Transition Table
# Maps each OrderStatusEnum value to the set of statuses it may transition to.
# Terminal states map to an empty set -- no further transitions allowed.

VALID_TRANSITIONS: dict[OrderStatusEnum, set[OrderStatusEnum]] = {
    OrderStatusEnum.PENDING_RISK: {
        OrderStatusEnum.RISK_APPROVED,
        OrderStatusEnum.RISK_REJECTED,
    },
    OrderStatusEnum.RISK_APPROVED: {
        OrderStatusEnum.SUBMITTED,
        OrderStatusEnum.REJECTED,
        OrderStatusEnum.CANCELLED,
    },
    OrderStatusEnum.SUBMITTED: {
        OrderStatusEnum.ACKNOWLEDGED,
        OrderStatusEnum.REJECTED,
    },
    OrderStatusEnum.ACKNOWLEDGED: {
        OrderStatusEnum.PARTIAL_FILL,
        OrderStatusEnum.FILLED,
        OrderStatusEnum.CANCELLED,
        OrderStatusEnum.EXPIRED,
    },
    OrderStatusEnum.PARTIAL_FILL: {
        OrderStatusEnum.PARTIAL_FILL,
        OrderStatusEnum.FILLED,
        OrderStatusEnum.CANCELLED,
    },
    # Terminal states -- no outgoing transitions
    OrderStatusEnum.RISK_REJECTED: set(),
    OrderStatusEnum.REJECTED: set(),
    OrderStatusEnum.FILLED: set(),
    OrderStatusEnum.CANCELLED: set(),
    OrderStatusEnum.EXPIRED: set(),
}

TERMINAL_STATES: set[OrderStatusEnum] = {status for status, allowed in VALID_TRANSITIONS.items() if len(allowed) == 0}

# Map DB enum values to proto enum values for event serialization
_STATUS_TO_PROTO: dict[OrderStatusEnum, int] = {
    OrderStatusEnum.PENDING_RISK: OrderStatus.ORDER_STATUS_PENDING_RISK,
    OrderStatusEnum.RISK_APPROVED: OrderStatus.ORDER_STATUS_RISK_APPROVED,
    OrderStatusEnum.RISK_REJECTED: OrderStatus.ORDER_STATUS_RISK_REJECTED,
    OrderStatusEnum.SUBMITTED: OrderStatus.ORDER_STATUS_SUBMITTED,
    OrderStatusEnum.ACKNOWLEDGED: OrderStatus.ORDER_STATUS_ACKNOWLEDGED,
    OrderStatusEnum.PARTIAL_FILL: OrderStatus.ORDER_STATUS_PARTIAL_FILL,
    OrderStatusEnum.FILLED: OrderStatus.ORDER_STATUS_FILLED,
    OrderStatusEnum.CANCELLED: OrderStatus.ORDER_STATUS_CANCELLED,
    OrderStatusEnum.REJECTED: OrderStatus.ORDER_STATUS_REJECTED,
    OrderStatusEnum.EXPIRED: OrderStatus.ORDER_STATUS_EXPIRED,
}


class OrderStateMachine:
    """Manages order lifecycle transitions with persistence and event publishing.

    Every transition:
      1. Validates the move is legal per VALID_TRANSITIONS.
      2. Updates the Order row inside a DB transaction.
      3. Creates an immutable OrderEvent protobuf.
      4. Publishes the event to Kafka topic ``pyhron.orders.events``.

    Usage::

        sm = OrderStateMachine(producer)
        event = await sm.transition(
            order=order,
            to_status=OrderStatusEnum.SUBMITTED,
            event_data={"broker_order_id": "abc123"},
            source="broker_ws",
        )
    """

    def __init__(self, producer: PyhronProducer) -> None:
        """Initialize with a Kafka producer for event publishing.

        Args:
            producer: The PyhronProducer instance for publishing order events.
        """
        self._producer = producer

    async def transition(
        self,
        order: Order,
        to_status: OrderStatusEnum,
        event_data: dict[str, object],
        source: str,
    ) -> OrderEventProto:
        """Execute a validated state transition for the given order.

        Args:
            order: The Order ORM instance whose status will change.
            to_status: Target status to transition to.
            event_data: Additional data for the event (filled_quantity,
                filled_price, commission, tax, rejection_reason, broker_order_id).
            source: Origin of the transition (e.g. "broker_ws", "reconciliation").

        Returns:
            The published OrderEventProto instance.

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        from_status = order.status

        # Validate the transition
        allowed = VALID_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition order {order.client_order_id} from {from_status.value} to {to_status.value}",
                from_status=from_status.value,
                to_status=to_status.value,
            )

        now = datetime.now(tz=UTC)

        # Persist the status change inside a transaction
        async with get_session() as session:
            update_values: dict[str, object] = {
                "status": to_status,
                "updated_at": now,
            }

            # Set timestamp columns based on target status
            if to_status == OrderStatusEnum.SUBMITTED:
                update_values["submitted_at"] = now
                if "broker_order_id" in event_data:
                    update_values["broker_order_id"] = event_data["broker_order_id"]

            elif to_status == OrderStatusEnum.ACKNOWLEDGED:
                update_values["acknowledged_at"] = now

            elif to_status in (OrderStatusEnum.PARTIAL_FILL, OrderStatusEnum.FILLED):
                if "filled_quantity" in event_data:
                    update_values["filled_quantity"] = int(cast(float, event_data["filled_quantity"]))
                if "avg_fill_price" in event_data:
                    update_values["avg_fill_price"] = event_data["avg_fill_price"]
                if to_status == OrderStatusEnum.FILLED:
                    update_values["filled_at"] = now

            if to_status == OrderStatusEnum.REJECTED:
                if "rejection_reason" in event_data:
                    update_values["rejection_reason"] = event_data["rejection_reason"]

            if "commission" in event_data:
                update_values["commission"] = event_data["commission"]
            if "tax" in event_data:
                update_values["tax"] = event_data["tax"]

            stmt = update(Order).where(Order.client_order_id == order.client_order_id).values(**update_values)
            await session.execute(stmt)

        # Build the protobuf event
        event = self._build_event(order, from_status, to_status, event_data, source, now)

        # Publish to Kafka
        await self._producer.send(
            Topics.ORDERS_EVENTS,
            event,
            key=order.client_order_id,
        )

        logger.info(
            "order_transition",
            client_order_id=order.client_order_id,
            from_status=from_status.value,
            to_status=to_status.value,
            source=source,
            event_id=event.event_id,
        )

        return event

    def _build_event(
        self,
        order: Order,
        from_status: OrderStatusEnum,
        to_status: OrderStatusEnum,
        event_data: dict[str, object],
        source: str,
        now: datetime,
    ) -> OrderEventProto:
        """Construct an OrderEventProto from transition data.

        Args:
            order: The order being transitioned.
            from_status: Previous status.
            to_status: New status.
            event_data: Additional fill/rejection data.
            source: Transition source identifier.
            now: Timestamp for the event.

        Returns:
            Populated OrderEventProto ready for Kafka publishing.
        """
        event = OrderEventProto()
        event.event_id = str(uuid.uuid4())
        event.client_order_id = order.client_order_id
        event.broker_order_id = str(event_data.get("broker_order_id", "")) or (order.broker_order_id or "")
        event.from_status = _STATUS_TO_PROTO[from_status]
        event.to_status = _STATUS_TO_PROTO[to_status]
        event.filled_quantity = cast(float, event_data.get("filled_quantity", 0))
        event.filled_price = cast(float, event_data.get("filled_price", 0))
        event.commission = cast(float, event_data.get("commission", 0))
        event.tax = cast(float, event_data.get("tax", 0))
        event.rejection_reason = str(event_data.get("rejection_reason", ""))
        event.source = source

        ts = Timestamp()
        ts.FromDatetime(now)
        event.occurred_at.CopyFrom(ts)

        return event
