"""Strategy signal Kafka consumer for paper trading.

Subscribes to strategy signal topics (momentum, ML), groups signals by
strategy/session, fetches last prices, and routes them through the
PaperStrategyExecutor for simulated execution.

Publishes rebalance results to ``pyhron.paper.rebalance_result``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from sqlalchemy import select

from data_platform.database_models.paper_trading_session import PaperTradingSession
from services.paper_trading.strategy_executor import PaperStrategyExecutor, RebalanceResult
from shared.async_database_session import get_session
from shared.configuration_settings import get_config
from shared.kafka_topics import KafkaTopic
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# How many signals to batch before executing a rebalance
DEFAULT_BATCH_SIZE = 50
# Max seconds to wait before flushing a partial batch
DEFAULT_BATCH_TIMEOUT_S = 5.0


@dataclass
class ConsumerHealthStatus:
    """Snapshot of consumer health for monitoring."""

    running: bool = False
    started_at: datetime | None = None
    last_message_at: datetime | None = None
    messages_processed: int = 0
    batches_flushed: int = 0
    errors: int = 0
    topics: list[str] = field(default_factory=list)
    consumer_group: str = ""

    @property
    def status(self) -> str:
        if not self.running:
            return "stopped"
        if self.errors > self.messages_processed * 0.1 and self.messages_processed > 0:
            return "degraded"
        return "healthy"


class StrategySignalKafkaConsumer:
    """Consumes strategy signals from Kafka and routes to paper trading executor.

    Subscribes to both momentum and ML signal topics. Signals are JSON-encoded
    with the following schema::

        {
            "strategy_id": "uuid-string",
            "session_id": "uuid-string",   // paper trading session
            "symbol": "BBCA",
            "target_weight": "0.15",
            "signal_source": "momentum",
            "alpha_score": "0.72",
            "last_price": "9250",          // optional — fetched from cache if absent
            "generated_at": "2025-01-15T09:30:00Z"
        }

    Usage::

        consumer = StrategySignalKafkaConsumer()
        await consumer.start()
        await consumer.run()  # blocks, processing signals continuously
    """

    def __init__(
        self,
        executor: PaperStrategyExecutor | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_timeout_s: float = DEFAULT_BATCH_TIMEOUT_S,
    ) -> None:
        config = get_config()
        self._bootstrap_servers: str = config.kafka_bootstrap_servers
        self._consumer: AIOKafkaConsumer | None = None
        self._producer: AIOKafkaProducer | None = None
        self._executor = executor or PaperStrategyExecutor()
        self._batch_size = batch_size
        self._batch_timeout_s = batch_timeout_s
        self._running = False
        self._started_at: datetime | None = None
        self._last_message_at: datetime | None = None
        self._messages_processed = 0
        self._batches_flushed = 0
        self._errors = 0

    async def start(self) -> None:
        """Start the Kafka consumer and producer."""
        self._consumer = AIOKafkaConsumer(
            KafkaTopic.MOMENTUM_SIGNALS,
            KafkaTopic.ML_SIGNALS,
            bootstrap_servers=self._bootstrap_servers,
            group_id="paper-strategy-executor",
            auto_offset_reset="latest",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode()),
            key_deserializer=lambda k: k.decode() if k else None,
        )
        await self._consumer.start()

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            value_serializer=lambda v: json.dumps(v).encode(),
            key_serializer=lambda k: k.encode() if k else None,
        )
        await self._producer.start()

        self._running = True
        self._started_at = datetime.now(UTC)
        logger.info(
            "strategy_signal_consumer_started",
            topics=[KafkaTopic.MOMENTUM_SIGNALS, KafkaTopic.ML_SIGNALS],
        )

    async def stop(self) -> None:
        """Stop the Kafka consumer and producer."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
        if self._producer:
            await self._producer.stop()
            self._producer = None
        logger.info("strategy_signal_consumer_stopped")

    def health(self) -> ConsumerHealthStatus:
        """Return a snapshot of consumer health metrics."""
        return ConsumerHealthStatus(
            running=self._running,
            started_at=self._started_at,
            last_message_at=self._last_message_at,
            messages_processed=self._messages_processed,
            batches_flushed=self._batches_flushed,
            errors=self._errors,
            topics=[KafkaTopic.MOMENTUM_SIGNALS, KafkaTopic.ML_SIGNALS],
            consumer_group="paper-strategy-executor",
        )

    async def run(self) -> None:
        """Main processing loop: consume signals, batch by session, execute.

        Raises:
            RuntimeError: If the consumer has not been started.
        """
        if not self._consumer:
            raise RuntimeError("Consumer not started — call start() first")

        # Buffer signals grouped by session_id
        buffer: dict[str, list[dict[str, Any]]] = {}
        last_flush = datetime.now(UTC)

        async for record in self._consumer:
            if not self._running:
                break

            try:
                self._messages_processed += 1
                self._last_message_at = datetime.now(UTC)
                signal = record.value
                session_id = signal.get("session_id", "")
                if not session_id:
                    logger.warning("signal_missing_session_id", signal=signal)
                    await self._consumer.commit()
                    continue

                buffer.setdefault(session_id, []).append(signal)

                # Flush conditions: batch full or timeout elapsed
                now = datetime.now(UTC)
                elapsed = (now - last_flush).total_seconds()
                should_flush = (
                    any(len(sigs) >= self._batch_size for sigs in buffer.values()) or elapsed >= self._batch_timeout_s
                )

                if should_flush:
                    await self._flush_buffer(buffer)
                    buffer.clear()
                    last_flush = now

                await self._consumer.commit()

            except Exception:
                self._errors += 1
                logger.exception(
                    "signal_processing_error",
                    topic=record.topic,
                    partition=record.partition,
                    offset=record.offset,
                )
                await self._consumer.commit()

        # Flush remaining signals on shutdown
        if buffer:
            await self._flush_buffer(buffer)

    async def _flush_buffer(self, buffer: dict[str, list[dict[str, Any]]]) -> None:
        """Process all buffered signals grouped by session."""
        self._batches_flushed += 1
        for session_id, signals in buffer.items():
            try:
                result = await self._execute_rebalance(session_id, signals)
                if result:
                    await self._publish_result(result)
            except Exception:
                logger.exception(
                    "rebalance_execution_failed",
                    session_id=session_id,
                    signal_count=len(signals),
                )

    async def _execute_rebalance(
        self,
        session_id: str,
        signals: list[dict[str, Any]],
    ) -> RebalanceResult | None:
        """Execute a rebalance for a paper trading session."""
        async with get_session() as db_session:
            # Load the paper trading session
            result = await db_session.execute(
                select(PaperTradingSession).where(
                    PaperTradingSession.id == session_id,
                    PaperTradingSession.status == "RUNNING",
                )
            )
            session = result.scalar_one_or_none()
            if not session:
                logger.warning(
                    "paper_session_not_found_or_not_running",
                    session_id=session_id,
                )
                return None

            # Extract last prices from signals or use cached prices
            last_prices = self._extract_last_prices(signals)

            # Execute rebalance through the strategy executor
            rebalance_result = await self._executor.process_rebalance_signal(
                session=session,
                signals=signals,
                last_prices=last_prices,
                db_session=db_session,
            )

            logger.info(
                "rebalance_completed",
                session_id=session_id,
                signals_consumed=rebalance_result.signals_consumed,
                orders_submitted=rebalance_result.orders_submitted,
                orders_rejected=rebalance_result.orders_rejected,
                turnover_idr=str(rebalance_result.estimated_turnover_idr),
            )

            return rebalance_result

    def _extract_last_prices(self, signals: list[dict[str, Any]]) -> dict[str, Decimal]:
        """Extract last prices from signal payloads.

        Each signal may include a ``last_price`` field. If multiple signals
        reference the same symbol, the latest price is used.
        """
        prices: dict[str, Decimal] = {}
        for sig in signals:
            symbol = sig.get("symbol", "")
            price_str = sig.get("last_price")
            if symbol and price_str:
                try:
                    prices[symbol] = Decimal(str(price_str))
                except Exception:
                    logger.warning("invalid_last_price", symbol=symbol, price=price_str)
        return prices

    async def _publish_result(self, result: RebalanceResult) -> None:
        """Publish rebalance result to Kafka."""
        if not self._producer:
            return

        payload = {
            "session_id": result.session_id,
            "rebalance_at": result.rebalance_at.isoformat(),
            "signals_consumed": result.signals_consumed,
            "orders_submitted": result.orders_submitted,
            "orders_rejected": result.orders_rejected,
            "estimated_turnover_idr": str(result.estimated_turnover_idr),
            "instructions": [
                {
                    "symbol": instr.symbol,
                    "side": instr.side,
                    "quantity_lots": instr.quantity_lots,
                    "order_type": instr.order_type,
                    "signal_source": instr.signal_source,
                }
                for instr in result.instructions
            ],
        }

        try:
            await self._producer.send_and_wait(
                KafkaTopic.PAPER_REBALANCE_RESULT,
                value=payload,
                key=result.session_id,
            )
            logger.debug(
                "rebalance_result_published",
                session_id=result.session_id,
                topic=KafkaTopic.PAPER_REBALANCE_RESULT,
            )
        except KafkaError:
            logger.exception(
                "rebalance_result_publish_failed",
                session_id=result.session_id,
            )
