"""Order submission service for the Pyhron OMS.

Consumes risk decisions from Kafka, submits approved orders to brokers,
handles broker rejections, and tracks fill accumulation.

Stateless consumer — all state from DB/Redis. Kafka provides ordering guarantees.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from google.protobuf.timestamp_pb2 import Timestamp
from sqlalchemy import select

from data_platform.models.trading import Order, OrderStatusEnum
from services.broker.base import BrokerAdapter
from services.oms.state_machine import OrderStateMachine
from shared.cache import get_redis
from shared.config import get_config
from shared.database import get_session
from shared.exceptions import BrokerConnectionError, BrokerTimeoutError, OrderRejectedError
from shared.logging import get_logger
from shared.messaging import PyhronConsumer, PyhronProducer, Topics
from shared.proto_generated.equity_orders_pb2 import (
    OrderRequest,
    OrderStatus,
    RiskDecision,
)

logger = get_logger(__name__)

# Redis key for idempotency tracking
IDEMPOTENCY_KEY_PREFIX = "pyhron:oms:submitted:"
IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours

# Risk decision status constants matching proto enum
RISK_APPROVED = 2
RISK_REJECTED = 3


class OrderSubmitter:
    """Consumes risk-approved orders and submits them to the appropriate broker.

    Lifecycle:
      1. Consume RiskDecision from ``pyhron.orders.risk-decisions``.
      2. Filter: only process RISK_APPROVED decisions (status == 2).
      3. Idempotency: skip if already submitted (DB + Redis check).
      4. Lookup the Order in DB, resolve the correct BrokerAdapter.
      5. Submit to broker; on success transition to SUBMITTED.
      6. On broker rejection: transition to REJECTED.
      7. Track cumulative fills for partial fill handling.

    Usage::

        submitter = OrderSubmitter(broker_registry={"ALPACA": alpaca_adapter})
        await submitter.start()
        await submitter.run()
    """

    def __init__(
        self,
        broker_registry: dict[str, BrokerAdapter],
    ) -> None:
        self._broker_registry = broker_registry
        self._config = get_config()
        self._bootstrap_servers = self._config.kafka_bootstrap_servers
        self._consumer: PyhronConsumer[RiskDecision] | None = None
        self._producer: PyhronProducer | None = None
        self._state_machine: OrderStateMachine | None = None

    async def start(self) -> None:
        """Initialize Kafka consumer, producer, and state machine."""
        self._consumer = PyhronConsumer(
            bootstrap_servers=self._bootstrap_servers,
            topic=Topics.ORDERS_RISK_DECISIONS,
            proto_type=RiskDecision,
            group_id="oms-submitter",
            dlq_topic=Topics.DLQ_ORDERS,
        )
        await self._consumer.start()

        self._producer = PyhronProducer(self._bootstrap_servers)
        await self._producer.start()

        self._state_machine = OrderStateMachine(self._producer)

        logger.info("order_submitter_started")

    async def stop(self) -> None:
        """Shut down consumer and producer gracefully."""
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()
        logger.info("order_submitter_stopped")

    async def run(self) -> None:
        """Main processing loop: consume risk decisions and submit approved orders."""
        if not self._consumer:
            raise RuntimeError("OrderSubmitter not started — call start() first")

        async for decision in self._consumer.stream():
            try:
                await self._process_decision(decision)
            except Exception:
                logger.exception(
                    "order_submission_failed",
                    client_order_id=decision.client_order_id,
                )

    async def _process_decision(self, decision: RiskDecision) -> None:
        """Process a single risk decision message.

        Args:
            decision: The RiskDecision protobuf from the risk engine.
        """
        # Only process approved decisions
        if decision.status != RISK_APPROVED:
            logger.debug(
                "skipping_non_approved_decision",
                client_order_id=decision.client_order_id,
                status=decision.status,
            )
            return

        client_order_id = decision.client_order_id

        # Idempotency check via Redis
        redis = await get_redis()
        idempotency_key = f"{IDEMPOTENCY_KEY_PREFIX}{client_order_id}"
        already_processed = await redis.get(idempotency_key)
        if already_processed:
            logger.warning(
                "duplicate_submission_skipped",
                client_order_id=client_order_id,
            )
            return

        # Idempotency check via DB — ensure order exists and is in RISK_APPROVED state
        order = await self._fetch_order(client_order_id)
        if order is None:
            logger.error(
                "order_not_found_for_submission",
                client_order_id=client_order_id,
            )
            return

        if order.status != OrderStatusEnum.RISK_APPROVED:
            logger.warning(
                "order_not_in_approved_state",
                client_order_id=client_order_id,
                current_status=order.status.value,
            )
            return

        # Mark as processing in Redis (set before broker call for crash safety)
        await redis.set(idempotency_key, "processing", ex=IDEMPOTENCY_TTL_SECONDS)

        # Resolve broker adapter based on order exchange
        adapter = self._resolve_broker(order.exchange)
        if adapter is None:
            logger.error(
                "no_broker_adapter_for_exchange",
                client_order_id=client_order_id,
                exchange=order.exchange,
            )
            return

        # Submit to broker
        await self._submit_to_broker(order, adapter, decision)

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

    def _resolve_broker(self, exchange: str) -> BrokerAdapter | None:
        """Resolve the broker adapter for the given exchange.

        Args:
            exchange: Exchange identifier (e.g. "ALPACA", "IDX").

        Returns:
            The matching BrokerAdapter, or None if no adapter is registered.
        """
        adapter = self._broker_registry.get(exchange.upper())
        if adapter is None:
            logger.error(
                "broker_adapter_not_found",
                exchange=exchange,
                available=list(self._broker_registry.keys()),
            )
        return adapter

    async def _submit_to_broker(
        self,
        order: Order,
        adapter: BrokerAdapter,
        decision: RiskDecision,
    ) -> None:
        """Submit an order to the broker and handle the response.

        On success: transitions order to SUBMITTED with broker_order_id.
        On rejection: transitions order to REJECTED with rejection reason.
        On connection/timeout error: logs error and leaves order in RISK_APPROVED
        for retry on next consumer restart.

        Args:
            order: The Order ORM instance.
            adapter: The resolved BrokerAdapter.
            decision: The original RiskDecision for metadata.
        """
        order_request = self._build_order_request(order, decision)

        try:
            broker_order_id = await adapter.submit_order(order_request)

            # Transition to SUBMITTED
            await self._state_machine.transition(
                order=order,
                to_status=OrderStatusEnum.SUBMITTED,
                event_data={
                    "broker_order_id": broker_order_id,
                },
                source="oms_submitter",
            )

            # Update idempotency key to mark as successfully submitted
            redis = await get_redis()
            idempotency_key = f"{IDEMPOTENCY_KEY_PREFIX}{order.client_order_id}"
            await redis.set(idempotency_key, "submitted", ex=IDEMPOTENCY_TTL_SECONDS)

            logger.info(
                "order_submitted_to_broker",
                client_order_id=order.client_order_id,
                broker_order_id=broker_order_id,
                exchange=order.exchange,
            )

        except OrderRejectedError as exc:
            # Broker explicitly rejected the order
            await self._state_machine.transition(
                order=order,
                to_status=OrderStatusEnum.REJECTED,
                event_data={
                    "rejection_reason": exc.reason or str(exc),
                    "broker_order_id": exc.broker_order_id,
                },
                source="oms_submitter",
            )

            redis = await get_redis()
            idempotency_key = f"{IDEMPOTENCY_KEY_PREFIX}{order.client_order_id}"
            await redis.set(idempotency_key, "rejected", ex=IDEMPOTENCY_TTL_SECONDS)

            logger.warning(
                "order_rejected_by_broker",
                client_order_id=order.client_order_id,
                reason=exc.reason,
                exchange=order.exchange,
            )

        except (BrokerConnectionError, BrokerTimeoutError) as exc:
            # Transient error — clear idempotency key so it can be retried
            redis = await get_redis()
            idempotency_key = f"{IDEMPOTENCY_KEY_PREFIX}{order.client_order_id}"
            await redis.delete(idempotency_key)

            logger.error(
                "broker_submission_transient_error",
                client_order_id=order.client_order_id,
                exchange=order.exchange,
                error=str(exc),
            )

    def _build_order_request(
        self,
        order: Order,
        decision: RiskDecision,
    ) -> OrderRequest:
        """Build a protobuf OrderRequest from the DB Order and RiskDecision.

        Args:
            order: The Order ORM instance.
            decision: The RiskDecision with approved quantity.

        Returns:
            A populated OrderRequest protobuf.
        """
        request = OrderRequest()
        request.client_order_id = order.client_order_id
        request.strategy_id = order.strategy_id
        request.symbol = order.symbol
        request.exchange = order.exchange

        # Map DB side to proto side
        if order.side == "BUY":
            request.side = 1  # ORDER_SIDE_BUY
        else:
            request.side = 2  # ORDER_SIDE_SELL

        # Map DB order type to proto order type
        order_type_map = {
            "MARKET": 1,
            "LIMIT": 2,
            "STOP": 3,
            "STOP_LIMIT": 4,
        }
        request.order_type = order_type_map.get(order.order_type, 1)

        # Use approved quantity from risk decision if available, else order quantity
        if decision.approved_quantity > 0:
            request.quantity = decision.approved_quantity
        else:
            request.quantity = order.quantity

        # Set price fields
        if order.limit_price is not None:
            request.limit_price = float(order.limit_price)
        if order.stop_price is not None:
            request.stop_price = float(order.stop_price)

        # Time in force
        tif_map = {
            "DAY": 1,
            "GTC": 2,
            "IOC": 3,
            "FOK": 4,
        }
        request.time_in_force = tif_map.get(order.time_in_force, 1)

        return request

    async def handle_fill(
        self,
        client_order_id: str,
        filled_quantity: int,
        filled_price: float,
        commission: float = 0.0,
        tax: float = 0.0,
    ) -> None:
        """Process a fill event from the broker, accumulating partial fills.

        Transitions order to PARTIAL_FILL or FILLED based on whether the
        cumulative filled quantity equals the total order quantity.

        Args:
            client_order_id: The order's client-assigned identifier.
            filled_quantity: Quantity filled in this execution.
            filled_price: Price of this execution.
            commission: Broker commission for this fill.
            tax: Tax charged on this fill.
        """
        order = await self._fetch_order(client_order_id)
        if order is None:
            logger.error(
                "fill_for_unknown_order",
                client_order_id=client_order_id,
            )
            return

        # Accumulate fills
        current_filled = order.filled_quantity or 0
        cumulative_filled = current_filled + filled_quantity

        # Compute volume-weighted average price
        current_avg = order.avg_fill_price or 0.0
        if cumulative_filled > 0:
            new_avg_price = (
                (current_avg * current_filled) + (filled_price * filled_quantity)
            ) / cumulative_filled
        else:
            new_avg_price = filled_price

        # Determine target status
        if cumulative_filled >= order.quantity:
            target_status = OrderStatusEnum.FILLED
        else:
            target_status = OrderStatusEnum.PARTIAL_FILL

        event_data = {
            "filled_quantity": cumulative_filled,
            "filled_price": filled_price,
            "avg_fill_price": new_avg_price,
            "commission": commission,
            "tax": tax,
        }

        await self._state_machine.transition(
            order=order,
            to_status=target_status,
            event_data=event_data,
            source="broker_fill",
        )

        logger.info(
            "fill_processed",
            client_order_id=client_order_id,
            this_fill_qty=filled_quantity,
            cumulative_filled=cumulative_filled,
            total_quantity=order.quantity,
            status=target_status.value,
        )
