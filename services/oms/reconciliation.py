"""Position reconciliation service for the Pyhron OMS.

Periodically compares internal position state (database) against broker-reported
positions and flags discrepancies. On mismatch: logs CRITICAL, publishes a
RiskBreachEvent to Kafka, and sets a circuit breaker in Redis to halt trading.

Runs every 5 minutes during market hours.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, time, timezone
from decimal import Decimal

from google.protobuf.timestamp_pb2 import Timestamp
from sqlalchemy import select

from data_platform.models.trading import Order, OrderStatusEnum
from services.broker.base import BrokerAdapter
from shared.redis_cache_client import get_redis
from shared.configuration_settings import get_config
from shared.async_database_session import get_session
from shared.structured_json_logger import get_logger
from shared.kafka_producer_consumer import PyhronProducer, Topics
from shared.proto_generated.pre_trade_risk_pb2 import RiskBreachEvent, RiskLimitType

logger = get_logger(__name__)

# Market hours (UTC) — configurable per exchange in production
MARKET_OPEN_UTC = time(13, 30)   # NYSE 9:30 ET = 13:30 UTC
MARKET_CLOSE_UTC = time(20, 0)   # NYSE 16:00 ET = 20:00 UTC

# Reconciliation interval in seconds
RECONCILIATION_INTERVAL_SECONDS = 300  # 5 minutes

# Redis keys
CIRCUIT_BREAKER_KEY = "pyhron:risk:circuit_breaker:{strategy_id}"
CIRCUIT_BREAKER_TTL_SECONDS = 3600  # 1 hour

# Tolerance for floating-point position value comparison
POSITION_QUANTITY_TOLERANCE = 0
POSITION_VALUE_TOLERANCE = Decimal("0.01")


class PositionReconciler:
    """Compares internal positions against broker-reported positions.

    On discrepancy:
      - Logs at CRITICAL level for immediate alerting.
      - Publishes a RiskBreachEvent to ``pyhron.risk.breaches``.
      - Sets a circuit breaker key in Redis to halt new order submissions.

    Usage::

        reconciler = PositionReconciler(
            broker_adapters={"ALPACA": alpaca_adapter},
        )
        await reconciler.start()
        await reconciler.run()
    """

    def __init__(
        self,
        broker_adapters: dict[str, BrokerAdapter],
    ) -> None:
        self._broker_adapters = broker_adapters
        self._config = get_config()
        self._bootstrap_servers = self._config.kafka_bootstrap_servers
        self._producer: PyhronProducer | None = None
        self._running = False

    async def start(self) -> None:
        """Initialize the Kafka producer for breach event publishing."""
        self._producer = PyhronProducer(self._bootstrap_servers)
        await self._producer.start()
        self._running = True
        logger.info("position_reconciler_started")

    async def stop(self) -> None:
        """Stop the reconciler and shut down the producer."""
        self._running = False
        if self._producer:
            await self._producer.stop()
        logger.info("position_reconciler_stopped")

    async def run(self) -> None:
        """Periodic reconciliation loop.

        Runs every RECONCILIATION_INTERVAL_SECONDS during market hours.
        Outside market hours, sleeps until the next market open.
        """
        while self._running:
            now_utc = datetime.now(tz=timezone.utc)

            if self._is_market_hours(now_utc):
                try:
                    await self.reconcile()
                except Exception:
                    logger.exception("reconciliation_cycle_failed")
            else:
                logger.debug(
                    "outside_market_hours",
                    current_time=now_utc.isoformat(),
                )

            await asyncio.sleep(RECONCILIATION_INTERVAL_SECONDS)

    async def reconcile(self) -> None:
        """Execute a single reconciliation cycle across all broker adapters.

        For each registered broker adapter:
          1. Fetch internal positions from the database.
          2. Fetch broker-reported positions via the adapter.
          3. Compare quantities and flag discrepancies.
        """
        logger.info("reconciliation_cycle_started")
        discrepancies_found = 0

        for exchange, adapter in self._broker_adapters.items():
            try:
                exchange_discrepancies = await self._reconcile_exchange(
                    exchange, adapter
                )
                discrepancies_found += exchange_discrepancies
            except Exception:
                logger.exception(
                    "exchange_reconciliation_failed",
                    exchange=exchange,
                )

        if discrepancies_found == 0:
            logger.info("reconciliation_cycle_clean", exchanges=len(self._broker_adapters))
        else:
            logger.critical(
                "reconciliation_discrepancies_detected",
                total_discrepancies=discrepancies_found,
            )

    async def _reconcile_exchange(
        self,
        exchange: str,
        adapter: BrokerAdapter,
    ) -> int:
        """Reconcile positions for a single exchange.

        Args:
            exchange: Exchange identifier (e.g. "ALPACA").
            adapter: The broker adapter for this exchange.

        Returns:
            Number of discrepancies found.
        """
        # Fetch broker positions
        broker_positions = await adapter.get_positions()
        broker_position_map: dict[str, dict] = {}
        for pos in broker_positions:
            symbol = pos.get("symbol", "")
            broker_position_map[symbol] = pos

        # Fetch internal positions from DB
        internal_positions = await self._get_internal_positions(exchange)

        discrepancies = 0

        # Check every internal position against broker
        all_symbols = set(internal_positions.keys()) | set(broker_position_map.keys())

        for symbol in all_symbols:
            internal_qty = internal_positions.get(symbol, 0)
            broker_data = broker_position_map.get(symbol, {})
            broker_qty = int(broker_data.get("qty", broker_data.get("quantity", 0)))

            if abs(internal_qty - broker_qty) > POSITION_QUANTITY_TOLERANCE:
                discrepancies += 1
                await self._handle_discrepancy(
                    exchange=exchange,
                    symbol=symbol,
                    internal_qty=internal_qty,
                    broker_qty=broker_qty,
                )

        logger.info(
            "exchange_reconciliation_complete",
            exchange=exchange,
            symbols_checked=len(all_symbols),
            discrepancies=discrepancies,
        )

        return discrepancies

    async def _get_internal_positions(
        self,
        exchange: str,
    ) -> dict[str, int]:
        """Query the database for current position quantities by symbol.

        Aggregates filled order quantities to compute net positions per symbol
        for the given exchange.

        Args:
            exchange: Exchange identifier to filter positions.

        Returns:
            Dict mapping symbol to net quantity held.
        """
        async with get_session() as session:
            result = await session.execute(
                select(Order).where(
                    Order.exchange == exchange,
                    Order.status.in_([
                        OrderStatusEnum.FILLED,
                        OrderStatusEnum.PARTIAL_FILL,
                        OrderStatusEnum.ACKNOWLEDGED,
                    ]),
                )
            )
            orders = result.scalars().all()

        positions: dict[str, int] = {}
        for order in orders:
            symbol = order.symbol
            filled_qty = order.filled_quantity or 0
            if order.side == "BUY":
                positions[symbol] = positions.get(symbol, 0) + filled_qty
            else:
                positions[symbol] = positions.get(symbol, 0) - filled_qty

        return positions

    async def _handle_discrepancy(
        self,
        exchange: str,
        symbol: str,
        internal_qty: int,
        broker_qty: int,
    ) -> None:
        """Handle a position discrepancy between internal state and broker.

        Logs at CRITICAL level, publishes a RiskBreachEvent, and sets a
        circuit breaker in Redis.

        Args:
            exchange: Exchange where the discrepancy was found.
            symbol: The instrument symbol.
            internal_qty: Position quantity per internal records.
            broker_qty: Position quantity per broker records.
        """
        difference = broker_qty - internal_qty

        logger.critical(
            "position_discrepancy_detected",
            exchange=exchange,
            symbol=symbol,
            internal_qty=internal_qty,
            broker_qty=broker_qty,
            difference=difference,
        )

        # Publish RiskBreachEvent to Kafka
        await self._publish_breach_event(
            exchange=exchange,
            symbol=symbol,
            internal_qty=internal_qty,
            broker_qty=broker_qty,
        )

        # Set circuit breaker in Redis — halt trading for this exchange
        await self._set_circuit_breaker(exchange, symbol)

    async def _publish_breach_event(
        self,
        exchange: str,
        symbol: str,
        internal_qty: int,
        broker_qty: int,
    ) -> None:
        """Publish a RiskBreachEvent to the risk breaches topic.

        Args:
            exchange: Exchange where breach occurred.
            symbol: Instrument symbol.
            internal_qty: Internal position quantity.
            broker_qty: Broker-reported position quantity.
        """
        if not self._producer:
            logger.error("cannot_publish_breach_no_producer")
            return

        breach = RiskBreachEvent()
        breach.breach_id = str(uuid.uuid4())
        breach.symbol = symbol
        breach.strategy_id = exchange
        breach.action_taken = (
            f"CIRCUIT_BREAKER_SET: Position mismatch for {symbol} on {exchange}. "
            f"Internal={internal_qty}, Broker={broker_qty}"
        )

        now = Timestamp()
        now.FromDatetime(datetime.now(tz=timezone.utc))
        breach.occurred_at.CopyFrom(now)

        await self._producer.send(
            Topics.RISK_BREACHES,
            breach,
            key=f"{exchange}:{symbol}",
        )

        logger.info(
            "breach_event_published",
            breach_id=breach.breach_id,
            exchange=exchange,
            symbol=symbol,
        )

    async def _set_circuit_breaker(self, exchange: str, symbol: str) -> None:
        """Set a circuit breaker key in Redis to halt trading.

        Args:
            exchange: Exchange identifier.
            symbol: Instrument symbol with the discrepancy.
        """
        redis = await get_redis()

        # Set exchange-level circuit breaker
        cb_key = CIRCUIT_BREAKER_KEY.format(strategy_id=exchange)
        await redis.set(
            cb_key,
            f"POSITION_MISMATCH:{symbol}:{datetime.now(tz=timezone.utc).isoformat()}",
            ex=CIRCUIT_BREAKER_TTL_SECONDS,
        )

        logger.critical(
            "circuit_breaker_set",
            exchange=exchange,
            symbol=symbol,
            ttl_seconds=CIRCUIT_BREAKER_TTL_SECONDS,
        )

    @staticmethod
    def _is_market_hours(now_utc: datetime) -> bool:
        """Check if the current UTC time falls within market hours.

        Args:
            now_utc: Current datetime in UTC.

        Returns:
            True if within market hours, False otherwise.
        """
        current_time = now_utc.time()

        # Only run on weekdays (Monday=0 through Friday=4)
        if now_utc.weekday() > 4:
            return False

        return MARKET_OPEN_UTC <= current_time <= MARKET_CLOSE_UTC
