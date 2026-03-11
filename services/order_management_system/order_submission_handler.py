"""Order submission handler for the Pyhron OMS.

Consumes risk decisions from Kafka, submits approved orders to brokers,
handles broker rejections, and tracks fill accumulation.

Stateless consumer -- all state from DB/Redis. Kafka provides ordering guarantees.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from data_platform.models.trading import Order, OrderStatusEnum
from services.order_management_system.order_state_machine import OrderStateMachine
from services.pre_trade_risk_engine.circuit_breaker_state_manager import (
    CIRCUIT_BREAKER_KEY,
)
from shared.async_database_session import get_session
from shared.configuration_settings import get_config
from shared.kafka_producer_consumer import PyhronConsumer, PyhronProducer, Topics
from shared.platform_exception_hierarchy import (
    BrokerConnectionError,
    BrokerTimeoutError,
    OrderRejectedError,
    RiskCheckFailedError,
)
from shared.proto_generated.equity_orders_pb2 import (
    OrderRequest,
    RiskDecision,
)
from shared.redis_cache_client import get_redis
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from services.broker_connectivity.broker_adapter_interface import BrokerAdapterInterface

logger = get_logger(__name__)

# Redis key for idempotency tracking
IDEMPOTENCY_KEY_PREFIX = "pyhron:oms:submitted:"
IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours

# Risk decision status constants matching proto enum
RISK_APPROVED = 2
RISK_REJECTED = 3


class OrderSubmissionHandler:
    """Consumes risk-approved orders and submits them to the appropriate broker.

    Lifecycle:
      1. Consume RiskDecision from ``pyhron.orders.risk-decisions``.
      2. Filter: only process RISK_APPROVED decisions (status == 2).
      3. Idempotency: skip if already submitted (DB + Redis check).
      4. Lookup the Order in DB, resolve the correct BrokerAdapterInterface.
      5. Submit to broker; on success transition to SUBMITTED.
      6. On broker rejection: transition to REJECTED.
      7. Track cumulative fills for partial fill handling.

    Usage::

        handler = OrderSubmissionHandler(
            broker_registry={"ALPACA": alpaca_adapter},
        )
        await handler.start()
        await handler.run()
    """

    def __init__(
        self,
        broker_registry: dict[str, BrokerAdapterInterface],
    ) -> None:
        """Initialize the submission handler.

        Args:
            broker_registry: Mapping of exchange name to broker adapter instance.
        """
        self._broker_registry = broker_registry
        self._config = get_config()
        self._bootstrap_servers: str = self._config.kafka_bootstrap_servers
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

        logger.info("order_submission_handler_started")

    async def stop(self) -> None:
        """Shut down consumer and producer gracefully."""
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()
        logger.info("order_submission_handler_stopped")

    async def run(self) -> None:
        """Main processing loop: consume risk decisions and submit approved orders.

        Raises:
            RuntimeError: If the handler has not been started.
        """
        if not self._consumer:
            raise RuntimeError("OrderSubmissionHandler not started -- call start() first")

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
        # Circuit breaker check — must be the FIRST gate before any submission
        redis = await get_redis()
        strategy_cb_key = CIRCUIT_BREAKER_KEY.format(entity_id=decision.strategy_id)
        exchange_cb_key = CIRCUIT_BREAKER_KEY.format(entity_id=decision.exchange)
        if await redis.get(strategy_cb_key) or await redis.get(exchange_cb_key):
            logger.warning(
                "order_blocked_circuit_breaker",
                client_order_id=decision.client_order_id,
                strategy_id=decision.strategy_id,
                exchange=decision.exchange,
            )
            raise RiskCheckFailedError(
                "Circuit breaker is tripped",
                reasons=["trading_halted"],
            )

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

        # Idempotency check via DB -- ensure order exists and is in RISK_APPROVED state
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
        if order.exchange is None:
            logger.error(
                "order_missing_exchange",
                client_order_id=client_order_id,
            )
            return
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
            result = await session.execute(select(Order).where(Order.client_order_id == client_order_id))
            return result.scalar_one_or_none()

    def _resolve_broker(self, exchange: str) -> BrokerAdapterInterface | None:
        """Resolve the broker adapter for the given exchange.

        Args:
            exchange: Exchange identifier (e.g. "ALPACA", "IDX").

        Returns:
            The matching BrokerAdapterInterface, or None if no adapter is registered.
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
        adapter: BrokerAdapterInterface,
        decision: RiskDecision,
    ) -> None:
        """Submit an order to the broker and handle the response.

        On success: transitions order to SUBMITTED with broker_order_id.
        On rejection: transitions order to REJECTED with rejection reason.
        On connection/timeout error: logs error and leaves order in RISK_APPROVED
        for retry on next consumer restart.

        Args:
            order: The Order ORM instance.
            adapter: The resolved BrokerAdapterInterface.
            decision: The original RiskDecision for metadata.
        """
        assert self._state_machine is not None, "OrderSubmissionHandler not started"
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
                source="oms_submission_handler",
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
                source="oms_submission_handler",
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
            # Transient error -- clear idempotency key so it can be retried
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
        request.exchange = order.exchange or ""

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
            request.quantity = int(decision.approved_quantity)
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
        tif_value = order.time_in_force.value if order.time_in_force is not None else "DAY"
        request.time_in_force = tif_map.get(tif_value, 1)

        return request
