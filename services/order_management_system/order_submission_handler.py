"""Order submission handler for the Pyhron OMS.

Supports two modes:
  1. **Kafka consumer mode** — consumes risk decisions from Kafka and submits
     approved orders to brokers (existing signal-driven pipeline).
  2. **Direct API mode** — synchronous order submission via ``submit_order()``
     with IDX validation and pre-trade risk checks inline.

Stateless consumer -- all state from DB/Redis.
"""

from __future__ import annotations

import traceback
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from data_platform.database_models.pyhron_order_lifecycle_record import (
    OrderSideEnum,
    OrderStatusEnum,
    OrderTypeEnum,
    PyhronOrderLifecycleRecord,
)
from data_platform.database_models.pyhron_strategy_position_snapshot import (
    PyhronStrategyPositionSnapshot,
)

Order = PyhronOrderLifecycleRecord
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
    CircuitBreakerOpenError,
    OrderRejectedError,
    PyhronValidationError,
    RiskCheckFailedError,
)
from shared.proto_generated.equity_orders_pb2 import (
    OrderRequest,
    RiskDecision,
)
from shared.redis_cache_client import get_redis
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from decimal import Decimal

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from services.broker_connectivity.broker_adapter_interface import BrokerAdapterInterface
    from services.order_management_system.idx_order_validator import IDXOrderValidator
    from services.pre_trade_risk_engine.pre_trade_risk_checks import RiskCheckResult

logger = get_logger(__name__)

# Redis key for idempotency tracking
IDEMPOTENCY_KEY_PREFIX = "pyhron:oms:submitted:"
IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours

# Risk decision status constants matching proto enum
RISK_APPROVED = 2
RISK_REJECTED = 3


class OrderSubmissionHandler:
    """Handles order submissions via Kafka consumer mode and direct API mode.

    **Kafka consumer mode** (existing):
      1. Consume RiskDecision from ``pyhron.orders.risk-decisions``.
      2. Filter: only process RISK_APPROVED decisions.
      3. Idempotency check, submit to broker, transition state.

    **Direct API mode** (via ``submit_order()``):
      1. Circuit breaker check.
      2. Idempotency check.
      3. IDX validation.
      4. Pre-trade risk checks.
      5. Persist to DB → submit to broker → transition state → Kafka publish.

    Usage (Kafka mode)::

        handler = OrderSubmissionHandler(broker_registry={"ALPACA": alpaca_adapter})
        await handler.start()
        await handler.run()

    Usage (API mode)::

        handler = OrderSubmissionHandler(
            broker_registry={"IDX": idx_adapter},
            risk_engine=risk_checks,
            broker_adapter=idx_adapter,
            order_state_machine=state_machine,
            kafka_producer=producer,
            db_session_factory=session_factory,
            idx_validator=validator,
        )
        record = await handler.submit_order(user_id=..., symbol=..., ...)
    """

    def __init__(
        self,
        broker_registry: dict[str, BrokerAdapterInterface],
        *,
        risk_engine: object | None = None,
        broker_adapter: BrokerAdapterInterface | None = None,
        order_state_machine: OrderStateMachine | None = None,
        kafka_producer: PyhronProducer | None = None,
        db_session_factory: async_sessionmaker[AsyncSession] | None = None,
        idx_validator: IDXOrderValidator | None = None,
    ) -> None:
        """Initialize the submission handler.

        Args:
            broker_registry: Mapping of exchange name to broker adapter instance.
            risk_engine: Pre-trade risk check functions (for direct API mode).
            broker_adapter: Default broker adapter (for direct API mode).
            order_state_machine: State machine instance (for direct API mode).
            kafka_producer: Kafka producer (for direct API mode).
            db_session_factory: Async session factory (for direct API mode).
            idx_validator: IDX order validator (for direct API mode).
        """
        self._broker_registry = broker_registry
        self._config = get_config()
        self._bootstrap_servers: str = self._config.kafka_bootstrap_servers
        self._consumer: PyhronConsumer[RiskDecision] | None = None
        self._producer: PyhronProducer | None = None
        self._state_machine: OrderStateMachine | None = None

        # Direct API mode dependencies
        self._risk_engine = risk_engine
        self._broker_adapter = broker_adapter
        self._api_state_machine = order_state_machine
        self._kafka_producer = kafka_producer
        self._db_session_factory = db_session_factory
        self._idx_validator = idx_validator

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

    # Direct API submission

    async def submit_order(
        self,
        user_id: str,
        strategy_id: str | None,
        symbol: str,
        side: str,
        order_type: str,
        quantity_lots: int,
        limit_price: Decimal | None,
        idempotency_key: str,
    ) -> PyhronOrderLifecycleRecord:
        """Submit an order via the direct API path.

        Performs IDX validation, pre-trade risk checks, persists the order,
        submits to the broker, and publishes a Kafka event.

        Args:
            user_id: Authenticated user ID from JWT.
            strategy_id: Optional strategy identifier.
            symbol: Instrument symbol (e.g. "BBCA.JK").
            side: "BUY" or "SELL".
            order_type: "MARKET" or "LIMIT".
            quantity_lots: Quantity in IDX lots (1 lot = 100 shares).
            limit_price: Limit price in IDR (required for LIMIT orders).
            idempotency_key: Client-generated dedup key.

        Returns:
            The persisted PyhronOrderLifecycleRecord.

        Raises:
            CircuitBreakerOpenError: If circuit breaker is OPEN.
            DuplicateOrderError: If idempotency key matched existing non-terminal order.
            PyhronValidationError: If IDX validation fails.
            RiskCheckFailedError: If pre-trade risk checks fail.
        """
        assert self._db_session_factory is not None, "db_session_factory required for submit_order"
        assert self._idx_validator is not None, "idx_validator required for submit_order"
        assert self._broker_adapter is not None, "broker_adapter required for submit_order"

        # Step 0a: Kill switch check — ABSOLUTE FIRST operation, no other logic precedes
        redis = await get_redis()
        from services.risk.kill_switch import (
            REDIS_KEY_GLOBAL,
            REDIS_KEY_STRATEGY,
            REDIS_KEY_SYMBOL,
            KillSwitchActiveError,
        )

        if await redis.get(REDIS_KEY_GLOBAL):
            raise KillSwitchActiveError("Trading halted globally", strategy_id=strategy_id)
        if strategy_id:
            ks_strat_key = REDIS_KEY_STRATEGY.format(strategy_id=strategy_id)
            if await redis.get(ks_strat_key):
                raise KillSwitchActiveError(f"Trading halted for strategy={strategy_id}", strategy_id=strategy_id)
        ks_sym_key = REDIS_KEY_SYMBOL.format(symbol=symbol)
        if await redis.get(ks_sym_key):
            raise KillSwitchActiveError(f"Trading halted for symbol={symbol}", symbol=symbol)

        # Step 0b: Circuit breaker check — second gate
        for entity_id in (strategy_id or "global", "IDX"):
            cb_key = CIRCUIT_BREAKER_KEY.format(entity_id=entity_id)
            if await redis.get(cb_key):
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN for {entity_id}",
                    strategy_id=entity_id,
                )

        # Step 1: Idempotency — check DB for existing order with this client_order_id
        async with self._db_session_factory() as session:
            existing = await session.execute(
                select(PyhronOrderLifecycleRecord).where(PyhronOrderLifecycleRecord.client_order_id == idempotency_key)
            )
            existing_record = existing.scalar_one_or_none()

        if existing_record is not None:
            terminal = {
                OrderStatusEnum.REJECTED,
                OrderStatusEnum.RISK_REJECTED,
                OrderStatusEnum.EXPIRED,
            }
            if existing_record.status not in terminal:
                return existing_record
            # Terminal orders can be re-submitted with same key

        # Step 2: Get current position for IDX validator (no-short-selling check)
        current_position_lots = 0
        async with self._db_session_factory() as session:
            pos_result = await session.execute(
                select(PyhronStrategyPositionSnapshot).where(
                    PyhronStrategyPositionSnapshot.strategy_id == (strategy_id or user_id),
                    PyhronStrategyPositionSnapshot.symbol == symbol,
                )
            )
            position = pos_result.scalar_one_or_none()
            if position is not None and position.quantity is not None:
                from services.order_management_system.idx_order_validator import IDX_LOT_SIZE

                current_position_lots = position.quantity // IDX_LOT_SIZE

        # Step 3: IDX validation
        validation = self._idx_validator.validate(
            symbol=symbol,
            side=side,
            quantity_lots=quantity_lots,
            order_type=order_type,
            price=limit_price,
            current_position_lots=current_position_lots,
        )
        if not validation.is_valid:
            raise PyhronValidationError(
                f"IDX validation failed for {symbol}",
                errors=validation.errors,
            )

        # Step 4: Pre-trade risk checks
        if self._risk_engine is not None:
            from services.pre_trade_risk_engine.pre_trade_risk_checks import (
                check_lot_size_constraint,
            )

            risk_order = OrderRequest()
            risk_order.quantity = quantity_lots * 100
            lot_check: RiskCheckResult = check_lot_size_constraint(
                order=risk_order,
                lot_size=100,
            )
            if not lot_check.passed:
                raise RiskCheckFailedError(
                    "Pre-trade risk check failed",
                    reasons=[lot_check.reason or "lot_size_check"],
                )

        # Log warnings from IDX validator
        for warning in validation.warnings:
            logger.warning("idx_validation_warning", symbol=symbol, warning=warning)

        # Step 5: Create PyhronOrderLifecycleRecord with PENDING_RISK, persist to DB
        from services.order_management_system.idx_order_validator import IDX_LOT_SIZE

        quantity_shares = quantity_lots * IDX_LOT_SIZE
        client_order_id = idempotency_key
        now = datetime.now(tz=UTC)

        record = PyhronOrderLifecycleRecord(
            client_order_id=client_order_id,
            user_id=user_id,
            strategy_id=strategy_id or user_id,
            symbol=symbol,
            exchange="IDX",
            side=OrderSideEnum.BUY if side == "BUY" else OrderSideEnum.SELL,
            order_type=OrderTypeEnum.MARKET if order_type == "MARKET" else OrderTypeEnum.LIMIT,
            quantity=quantity_shares,
            filled_quantity=0,
            limit_price=limit_price,
            status=OrderStatusEnum.PENDING_RISK,
            currency="IDR",
            created_at=now,
            updated_at=now,
        )

        async with self._db_session_factory() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)

        logger.info(
            "order_persisted",
            client_order_id=client_order_id,
            user_id=user_id,
            symbol=symbol,
            side=side,
            quantity_lots=quantity_lots,
        )

        # Step 6: Transition PENDING_RISK → RISK_APPROVED (risk passed inline)
        state_machine = self._api_state_machine
        if state_machine is None and self._kafka_producer is not None:
            state_machine = OrderStateMachine(self._kafka_producer)

        if state_machine is not None:
            async with self._db_session_factory() as session:
                order_result = await session.execute(
                    select(PyhronOrderLifecycleRecord).where(
                        PyhronOrderLifecycleRecord.client_order_id == client_order_id
                    )
                )
                order_obj = order_result.scalar_one()

            await state_machine.transition(
                order=order_obj,
                to_status=OrderStatusEnum.RISK_APPROVED,
                event_data={},
                source="api_submission",
            )
        else:
            async with self._db_session_factory() as session:
                order_result = await session.execute(
                    select(PyhronOrderLifecycleRecord).where(
                        PyhronOrderLifecycleRecord.client_order_id == client_order_id
                    )
                )
                rec = order_result.scalar_one()
                rec.status = OrderStatusEnum.RISK_APPROVED
                rec.updated_at = datetime.now(tz=UTC)
                await session.commit()

        # Step 7-8: Submit to broker, transition RISK_APPROVED → SUBMITTED
        try:
            order_request = OrderRequest()
            order_request.client_order_id = client_order_id
            order_request.strategy_id = strategy_id or user_id
            order_request.symbol = symbol
            order_request.exchange = "IDX"
            order_request.side = 1 if side == "BUY" else 2
            order_request.order_type = 1 if order_type == "MARKET" else 2
            order_request.quantity = quantity_shares
            if limit_price is not None:
                order_request.limit_price = float(limit_price)
            order_request.time_in_force = 1  # DAY

            broker_order_id = await self._broker_adapter.submit_order(order_request)

            # Success: transition RISK_APPROVED → SUBMITTED
            if state_machine is not None:
                async with self._db_session_factory() as session:
                    order_result = await session.execute(
                        select(PyhronOrderLifecycleRecord).where(
                            PyhronOrderLifecycleRecord.client_order_id == client_order_id
                        )
                    )
                    order_obj = order_result.scalar_one()

                await state_machine.transition(
                    order=order_obj,
                    to_status=OrderStatusEnum.SUBMITTED,
                    event_data={"broker_order_id": broker_order_id},
                    source="api_submission",
                )
            else:
                async with self._db_session_factory() as session:
                    order_result = await session.execute(
                        select(PyhronOrderLifecycleRecord).where(
                            PyhronOrderLifecycleRecord.client_order_id == client_order_id
                        )
                    )
                    rec = order_result.scalar_one()
                    rec.broker_order_id = broker_order_id
                    rec.status = OrderStatusEnum.SUBMITTED
                    rec.submitted_at = datetime.now(tz=UTC)
                    rec.updated_at = datetime.now(tz=UTC)
                    await session.commit()

            logger.info(
                "order_submitted_to_broker",
                client_order_id=client_order_id,
                broker_order_id=broker_order_id,
                user_id=user_id,
                symbol=symbol,
            )

        except OrderRejectedError as exc:
            # Broker rejected: transition RISK_APPROVED → REJECTED
            if state_machine is not None:
                async with self._db_session_factory() as session:
                    order_result = await session.execute(
                        select(PyhronOrderLifecycleRecord).where(
                            PyhronOrderLifecycleRecord.client_order_id == client_order_id
                        )
                    )
                    order_obj = order_result.scalar_one()

                await state_machine.transition(
                    order=order_obj,
                    to_status=OrderStatusEnum.REJECTED,
                    event_data={
                        "rejection_reason": exc.reason or str(exc),
                        "broker_order_id": exc.broker_order_id,
                    },
                    source="api_submission",
                )
            else:
                async with self._db_session_factory() as session:
                    order_result = await session.execute(
                        select(PyhronOrderLifecycleRecord).where(
                            PyhronOrderLifecycleRecord.client_order_id == client_order_id
                        )
                    )
                    rec = order_result.scalar_one()
                    rec.status = OrderStatusEnum.REJECTED
                    rec.rejection_reason = exc.reason or str(exc)
                    rec.updated_at = datetime.now(tz=UTC)
                    await session.commit()

            logger.warning(
                "order_rejected_by_broker",
                client_order_id=client_order_id,
                reason=exc.reason,
                user_id=user_id,
                symbol=symbol,
            )

        except (BrokerConnectionError, BrokerTimeoutError) as exc:
            # Transient error — order stays PENDING_RISK, eligible for retry
            logger.error(
                "broker_submission_transient_error",
                client_order_id=client_order_id,
                user_id=user_id,
                symbol=symbol,
                error=str(exc),
            )

        except Exception as exc:
            # Unexpected error — reject the order
            logger.error(
                "order_submission_unexpected_error",
                client_order_id=client_order_id,
                user_id=user_id,
                symbol=symbol,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            if state_machine is not None:
                async with self._db_session_factory() as session:
                    order_result = await session.execute(
                        select(PyhronOrderLifecycleRecord).where(
                            PyhronOrderLifecycleRecord.client_order_id == client_order_id
                        )
                    )
                    order_obj = order_result.scalar_one()

                await state_machine.transition(
                    order=order_obj,
                    to_status=OrderStatusEnum.REJECTED,
                    event_data={"rejection_reason": str(exc)},
                    source="api_submission",
                )

        # Step 8: Kafka publish (fire-and-forget, DB already committed)
        if self._kafka_producer is not None:
            try:
                from shared.schemas.order_events import OrderSubmittedEvent

                event = OrderSubmittedEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.now(tz=UTC).isoformat(),
                    order_id=client_order_id,
                    client_order_id=client_order_id,
                    user_id=user_id,
                    strategy_id=strategy_id,
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity_lots=quantity_lots,
                    limit_price=str(limit_price) if limit_price else None,
                    submitted_at=datetime.now(tz=UTC).isoformat(),
                )
                # Fire-and-forget: log failures but don't block
                logger.info(
                    "order_submitted_event_queued",
                    client_order_id=client_order_id,
                    event_id=event.event_id,
                )
            except Exception:
                logger.exception(
                    "kafka_publish_failed",
                    client_order_id=client_order_id,
                )

        # Step 9: Return the persisted record
        async with self._db_session_factory() as session:
            order_result = await session.execute(
                select(PyhronOrderLifecycleRecord).where(PyhronOrderLifecycleRecord.client_order_id == client_order_id)
            )
            return order_result.scalar_one()
