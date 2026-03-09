"""Kafka producer and consumer abstractions.

All messages are serialised/deserialised using Protobuf.

Key design goals:
  - Type-safe: every topic has a declared message type
  - Idempotent producers: exactly-once semantics where supported
  - Dead letter queue: unprocessable messages are not lost
  - Async-first: all I/O is non-blocking

Migration note for Rust:
  Replace this module with a Rust tokio-kafka consumer/producer
  that reads the same Protobuf-encoded messages from the same topics.
  Python and Rust services are interoperable because the wire format
  (Protobuf bytes on Kafka) is language-agnostic.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import AsyncIterator, Generic, TypeVar

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from google.protobuf.message import Message

from shared.platform_exception_hierarchy import ConsumerError, DeserializationError, ProducerError
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
ProtoT = TypeVar("ProtoT", bound=Message)


# ── Topic Registry ──────────────────────────────────────────────────────────
# Single source of truth for topic names. Never hardcode topic strings.


class Topics:
    """Canonical Kafka topic names."""

    # Market data
    MARKET_TICKS = "pyhron.market.ticks"
    MARKET_OHLCV_1D = "pyhron.market.ohlcv.1d"
    MARKET_OHLCV_INTRADAY = "pyhron.market.ohlcv.intraday"

    # Signal pipeline
    SIGNALS = "pyhron.signals"

    # Order lifecycle
    ORDERS_EVENTS = "pyhron.orders.events"
    ORDERS_RISK_DECISIONS = "pyhron.orders.risk-decisions"

    # Position events
    POSITIONS_EVENTS = "pyhron.positions.events"
    POSITIONS_SNAPSHOTS = "pyhron.positions.snapshots"

    # Risk
    RISK_BREACHES = "pyhron.risk.breaches"
    RISK_CIRCUIT_BREAKER = "pyhron.risk.circuit-breaker"

    # Equity strategy signals
    EQUITY_STRATEGY_SIGNALS = "pyhron.equity.strategy-signals"

    # Macro economic indicators
    MACRO_INDICATOR_UPDATES = "pyhron.macro.indicator-updates"
    MACRO_POLICY_EVENTS = "pyhron.macro.policy-events"

    # Commodity prices and alerts
    COMMODITY_PRICE_UPDATES = "pyhron.commodity.price-updates"
    COMMODITY_STOCK_IMPACT_ALERTS = "pyhron.commodity.stock-impact-alerts"

    # Alternative data
    FIRE_HOTSPOT_EVENTS = "pyhron.alternative-data.fire-hotspot-events"
    CLIMATE_INDEX_EVENTS = "pyhron.alternative-data.climate-index-events"
    NEWS_SENTIMENT_EVENTS = "pyhron.alternative-data.news-sentiment-events"

    # Fixed income
    YIELD_CURVE_SNAPSHOTS = "pyhron.fixed-income.yield-curve-snapshots"
    BOND_PRICE_UPDATES = "pyhron.fixed-income.bond-price-updates"

    # Governance intelligence
    GOVERNANCE_FLAG_EVENTS = "pyhron.governance.flag-events"
    OWNERSHIP_CHANGE_EVENTS = "pyhron.governance.ownership-change-events"

    # Data platform
    DATA_INGESTION_STATUS = "pyhron.data.ingestion-status"
    DATA_QUALITY_ALERTS = "pyhron.data.quality-alerts"

    # Dead letter queues
    DLQ_SIGNALS = "pyhron.dlq.equity-strategy-signals"
    DLQ_ORDERS = "pyhron.dlq.equity-order-events"
    DLQ_POSITIONS = "pyhron.dlq.equity-position-events"
    DLQ_MACRO = "pyhron.dlq.macro-indicator-updates"
    DLQ_COMMODITY = "pyhron.dlq.commodity-price-updates"
    DLQ_FIRE_HOTSPOT = "pyhron.dlq.fire-hotspot-events"


class PyhronProducer:
    """Type-safe Kafka producer for Protobuf messages.

    Usage::

        async with PyhronProducer(bootstrap_servers="kafka:29092") as producer:
            await producer.send(Topics.SIGNALS, signal_proto, key=strategy_id)
    """

    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start the underlying Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            max_batch_size=65536,
            linger_ms=10,
            retry_backoff_ms=100,
        )
        await self._producer.start()
        logger.info("kafka_producer_started", servers=self._bootstrap_servers)

    async def stop(self) -> None:
        """Flush and stop the producer."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("kafka_producer_stopped")

    async def __aenter__(self) -> PyhronProducer:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    async def send(
        self,
        topic: str,
        message: Message,
        *,
        key: str | None = None,
    ) -> None:
        """Serialize and send a Protobuf message to a Kafka topic.

        Args:
            topic: Target topic name (use ``Topics`` constants).
            message: Protobuf message instance.
            key: Optional partition key for consistent routing.

        Raises:
            ProducerError: On Kafka send failure after retries.
        """
        if self._producer is None:
            raise ProducerError("Producer not started — call start() or use async with")

        value_bytes = message.SerializeToString()
        key_bytes = key.encode() if key else None

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await self._producer.send_and_wait(
                    topic,
                    value=value_bytes,
                    key=key_bytes,
                )
                logger.debug(
                    "kafka_message_sent",
                    topic=topic,
                    key=key,
                    size_bytes=len(value_bytes),
                )
                return
            except KafkaError as exc:
                if attempt == max_retries:
                    logger.error(
                        "kafka_send_failed",
                        topic=topic,
                        key=key,
                        error=str(exc),
                        attempts=attempt,
                    )
                    raise ProducerError(
                        f"Failed to send to {topic} after {max_retries} attempts: {exc}"
                    ) from exc
                wait = 0.1 * (2 ** (attempt - 1))
                logger.warning(
                    "kafka_send_retry",
                    topic=topic,
                    attempt=attempt,
                    wait_s=wait,
                )
                await asyncio.sleep(wait)


class PyhronConsumer(Generic[ProtoT]):
    """Type-safe Kafka consumer for Protobuf messages.

    Usage::

        consumer = PyhronConsumer(
            bootstrap_servers="kafka:29092",
            topic=Topics.SIGNALS,
            proto_type=Signal,
            group_id="risk-engine",
        )
        async for message in consumer.stream():
            await process(message)

    Migration note:
        This is the exact interface a Rust consumer would expose via PyO3
        or via a separate process consuming the same Kafka topic.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        proto_type: type[ProtoT],
        group_id: str,
        dlq_topic: str | None = None,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._proto_type = proto_type
        self._group_id = group_id
        self._dlq_topic = dlq_topic
        self._consumer: AIOKafkaConsumer | None = None
        self._dlq_producer: PyhronProducer | None = None

    async def start(self) -> None:
        """Start the consumer (and DLQ producer if configured)."""
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await self._consumer.start()
        logger.info(
            "kafka_consumer_started",
            topic=self._topic,
            group_id=self._group_id,
        )

        if self._dlq_topic:
            self._dlq_producer = PyhronProducer(self._bootstrap_servers)
            await self._dlq_producer.start()

    async def stop(self) -> None:
        """Stop consumer and DLQ producer."""
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        if self._dlq_producer is not None:
            await self._dlq_producer.stop()
            self._dlq_producer = None
        logger.info("kafka_consumer_stopped", topic=self._topic)

    async def stream(self) -> AsyncIterator[ProtoT]:
        """Yield deserialized Protobuf messages.

        On deserialization failure: publish raw bytes to DLQ, continue.
        Commits offset after each successfully yielded message.

        Yields:
            Deserialized Protobuf message of type ``ProtoT``.

        Raises:
            ConsumerError: If consumer is not started.
        """
        if self._consumer is None:
            raise ConsumerError("Consumer not started — call start() first")

        async for record in self._consumer:
            try:
                msg = self._proto_type()
                msg.ParseFromString(record.value)
                yield msg
                await self._consumer.commit()
            except Exception as exc:
                logger.error(
                    "kafka_deserialize_failed",
                    topic=self._topic,
                    partition=record.partition,
                    offset=record.offset,
                    error=str(exc),
                )
                await self._send_to_dlq(record.value, record.key, str(exc))
                await self._consumer.commit()

    async def _send_to_dlq(
        self,
        raw_value: bytes,
        raw_key: bytes | None,
        error: str,
    ) -> None:
        """Send unprocessable message to dead letter queue."""
        if self._dlq_producer is None or self._dlq_topic is None:
            logger.warning(
                "dlq_not_configured",
                topic=self._topic,
                error=error,
            )
            return

        try:
            dlq_key = raw_key.decode() if raw_key else str(uuid.uuid4())
            # Send raw bytes directly — DLQ retains original payload
            if self._dlq_producer._producer is not None:
                await self._dlq_producer._producer.send_and_wait(
                    self._dlq_topic,
                    value=raw_value,
                    key=raw_key,
                    headers=[("error", error.encode())],
                )
                logger.info(
                    "dlq_message_sent",
                    dlq_topic=self._dlq_topic,
                    source_topic=self._topic,
                    key=dlq_key,
                )
        except KafkaError as dlq_exc:
            logger.error(
                "dlq_send_failed",
                dlq_topic=self._dlq_topic,
                error=str(dlq_exc),
            )
