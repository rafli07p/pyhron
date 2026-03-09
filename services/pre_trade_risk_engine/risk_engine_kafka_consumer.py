"""Pre-trade risk engine Kafka consumer.

Consumes ``pyhron.signals``, constructs ``OrderRequest``, runs all checks,
publishes ``RiskDecision`` to ``pyhron.orders.risk-decisions``.

This service is stateless within a request -- all state read from DB/Redis.
Makes Rust migration trivial (same Kafka interface, same DB schema).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from google.protobuf.timestamp_pb2 import Timestamp

from services.pre_trade_risk_engine.pre_trade_risk_checks import (
    RiskCheckResult,
    check_daily_loss_limit,
    check_duplicate_order,
    check_lot_size_constraint,
    check_max_position_size,
    check_portfolio_var,
    check_signal_staleness,
)
from shared.configuration_settings import get_config
from shared.kafka_producer_consumer import PyhronConsumer, PyhronProducer, Topics
from shared.proto_generated.equity_orders_pb2 import (
    OrderRequest,
    OrderSide,
    OrderType,
    RiskDecision,
    TimeInForce,
)
from shared.proto_generated.equity_positions_pb2 import PortfolioSnapshot
from shared.proto_generated.pre_trade_risk_pb2 import RiskBreachEvent
from shared.proto_generated.strategy_signals_pb2 import Signal, SignalDirection
from shared.redis_cache_client import get_redis
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# Redis keys for circuit breaker and recent orders tracking
CIRCUIT_BREAKER_KEY = "pyhron:risk:circuit_breaker:{strategy_id}"
RECENT_ORDERS_KEY = "pyhron:risk:recent_orders"


class RiskEngineKafkaConsumer:
    """Pre-trade risk engine consuming signals from Kafka.

    Consumes signals from the ``pyhron.signals`` topic, runs all configured
    risk checks, and publishes risk decisions (approved or rejected) to
    ``pyhron.orders.risk-decisions``. Stateless -- all state from DB/Redis.

    Usage::

        engine = RiskEngineKafkaConsumer()
        await engine.start()
        await engine.run()
    """

    def __init__(self) -> None:
        config = get_config()
        self._config = config
        self._bootstrap_servers: str = config.kafka_bootstrap_servers
        self._max_position_pct: float = config.risk_max_position_size_pct
        self._max_sector_pct: float = config.risk_max_sector_concentration_pct
        self._daily_loss_pct: float = config.risk_daily_loss_limit_pct
        self._max_var_pct: float = config.risk_max_var_95_pct
        self._lot_size: int = config.risk_idx_lot_size
        self._consumer: PyhronConsumer[Signal] | None = None
        self._producer: PyhronProducer | None = None

    async def start(self) -> None:
        """Start the Kafka consumer and producer connections."""
        self._consumer = PyhronConsumer(
            bootstrap_servers=self._bootstrap_servers,
            topic=Topics.SIGNALS,
            proto_type=Signal,
            group_id="risk-engine",
            dlq_topic=Topics.DLQ_SIGNALS,
        )
        await self._consumer.start()

        self._producer = PyhronProducer(self._bootstrap_servers)
        await self._producer.start()

        logger.info("risk_engine_started")

    async def stop(self) -> None:
        """Stop the Kafka consumer and producer connections."""
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()
        logger.info("risk_engine_stopped")

    async def run(self) -> None:
        """Main processing loop: consume signals, evaluate, publish decisions.

        Raises:
            RuntimeError: If the engine has not been started.
        """
        if not self._consumer:
            raise RuntimeError("Engine not started")

        async for signal in self._consumer.stream():
            try:
                await self._evaluate_signal(signal)
            except Exception:
                logger.exception(
                    "risk_evaluation_failed",
                    signal_id=signal.signal_id,
                    strategy_id=signal.strategy_id,
                )

    async def _evaluate_signal(self, signal: Signal) -> None:
        """Evaluate a single signal through the risk check pipeline.

        Args:
            signal: The incoming strategy signal to evaluate.
        """
        redis = await get_redis()

        # Check circuit breaker first
        cb_key = CIRCUIT_BREAKER_KEY.format(strategy_id=signal.strategy_id)
        is_halted = await redis.get(cb_key)
        if is_halted:
            logger.warning(
                "circuit_breaker_active",
                strategy_id=signal.strategy_id,
            )
            await self._publish_rejection(signal, ["Circuit breaker is active for this strategy"])
            return

        # Construct OrderRequest from Signal
        order = self._signal_to_order(signal)

        # Fetch portfolio state (simplified -- in production, read from DB)
        portfolio = await self._get_portfolio_snapshot(signal.strategy_id)

        # Get recent orders for dedup check
        recent_orders = await redis.lrange(RECENT_ORDERS_KEY, 0, 999)
        if recent_orders is None:
            recent_orders = []

        # Run all checks -- fail fast on first rejection
        checks: list[RiskCheckResult] = []
        rejection_reasons: list[str] = []

        for check_fn, kwargs in [
            (check_lot_size_constraint, {"order": order, "lot_size": self._lot_size}),
            (
                check_daily_loss_limit,
                {
                    "portfolio": portfolio,
                    "daily_loss_limit_pct": self._daily_loss_pct,
                },
            ),
            (check_duplicate_order, {"order": order, "recent_orders": recent_orders}),
            (check_signal_staleness, {"order": order, "max_age_seconds": 300}),
            (
                check_max_position_size,
                {
                    "order": order,
                    "portfolio": portfolio,
                    "max_pct": self._max_position_pct,
                },
            ),
            (
                check_portfolio_var,
                {
                    "order": order,
                    "portfolio": portfolio,
                    "var_limit_pct": self._max_var_pct,
                },
            ),
        ]:
            result = check_fn(**kwargs)
            checks.append(result)
            if not result.passed:
                rejection_reasons.append(f"{result.check_name}: {result.reason}")
                break  # Fail fast

        if rejection_reasons:
            await self._publish_rejection(signal, rejection_reasons)
            await self._publish_breach(signal, checks)
        else:
            await self._publish_approval(signal, order, portfolio)
            # Track order for dedup
            await redis.lpush(RECENT_ORDERS_KEY, order.client_order_id)
            await redis.ltrim(RECENT_ORDERS_KEY, 0, 9999)
            await redis.expire(RECENT_ORDERS_KEY, 300)

        logger.info(
            "risk_evaluation_complete",
            signal_id=signal.signal_id,
            approved=len(rejection_reasons) == 0,
            checks_run=len(checks),
        )

    def _signal_to_order(self, signal: Signal) -> OrderRequest:
        """Convert a strategy Signal to an OrderRequest protobuf.

        Args:
            signal: The incoming strategy signal.

        Returns:
            A populated OrderRequest protobuf.
        """
        order = OrderRequest()
        order.client_order_id = str(uuid.uuid4())
        order.strategy_id = signal.strategy_id
        order.symbol = signal.symbol
        order.exchange = signal.exchange

        if signal.direction == SignalDirection.SIGNAL_DIRECTION_LONG:
            order.side = OrderSide.ORDER_SIDE_BUY
        elif (
            signal.direction == SignalDirection.SIGNAL_DIRECTION_SHORT
            or signal.direction == SignalDirection.SIGNAL_DIRECTION_CLOSE
        ):
            order.side = OrderSide.ORDER_SIDE_SELL
        else:
            order.side = OrderSide.ORDER_SIDE_BUY

        order.order_type = OrderType.ORDER_TYPE_MARKET
        order.time_in_force = TimeInForce.TIME_IN_FORCE_DAY
        order.signal_time.CopyFrom(signal.generated_at)

        return order

    async def _get_portfolio_snapshot(self, strategy_id: str) -> PortfolioSnapshot:
        """Fetch current portfolio state for a strategy.

        Args:
            strategy_id: The strategy identifier.

        Returns:
            A PortfolioSnapshot protobuf. Returns empty snapshot if unavailable.
        """
        # In production: query positions table + Redis-cached prices
        return PortfolioSnapshot(portfolio_id=strategy_id)

    async def _publish_approval(
        self,
        signal: Signal,
        order: OrderRequest,
        portfolio: PortfolioSnapshot,
    ) -> None:
        """Publish a RISK_APPROVED decision to Kafka.

        Args:
            signal: The original signal.
            order: The constructed order request.
            portfolio: The portfolio snapshot used for evaluation.
        """
        if not self._producer:
            return

        decision = RiskDecision()
        decision.client_order_id = order.client_order_id
        decision.status = 2  # RISK_APPROVED
        decision.approved_quantity = order.quantity
        decision.portfolio_var_before = portfolio.portfolio_var_95

        now = Timestamp()
        now.FromDatetime(datetime.now(tz=UTC))
        decision.decided_at.CopyFrom(now)

        await self._producer.send(
            Topics.ORDERS_RISK_DECISIONS,
            decision,
            key=order.client_order_id,
        )

    async def _publish_rejection(self, signal: Signal, reasons: list[str]) -> None:
        """Publish a RISK_REJECTED decision to Kafka.

        Args:
            signal: The original signal that was rejected.
            reasons: List of human-readable rejection reason strings.
        """
        if not self._producer:
            return

        decision = RiskDecision()
        decision.client_order_id = signal.signal_id
        decision.status = 3  # RISK_REJECTED
        decision.rejection_reasons.extend(reasons)

        now = Timestamp()
        now.FromDatetime(datetime.now(tz=UTC))
        decision.decided_at.CopyFrom(now)

        await self._producer.send(
            Topics.ORDERS_RISK_DECISIONS,
            decision,
            key=signal.signal_id,
        )

    async def _publish_breach(self, signal: Signal, checks: list[RiskCheckResult]) -> None:
        """Publish risk breach events for failed checks.

        Args:
            signal: The signal that triggered the breach.
            checks: List of risk check results (publishes events for failures).
        """
        if not self._producer:
            return

        for check in checks:
            if not check.passed:
                breach = RiskBreachEvent()
                breach.breach_id = str(uuid.uuid4())
                breach.symbol = signal.symbol
                breach.strategy_id = signal.strategy_id
                breach.action_taken = "ORDER_REJECTED"

                now = Timestamp()
                now.FromDatetime(datetime.now(tz=UTC))
                breach.occurred_at.CopyFrom(now)

                await self._producer.send(
                    Topics.RISK_BREACHES,
                    breach,
                    key=signal.strategy_id,
                )
