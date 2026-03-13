"""Processes failed records from DLQ topics.

Consumer group: pyhron-dlq-processor

Retry policy per record:
- Extract retry_count from record headers (default 0)
- If retry_count < MAX_RETRIES (3): re-validate and re-route
- If retry_count >= MAX_RETRIES: write to dlq_permanent table in DB
  for manual inspection; log at ERROR level with full context

The DLQ processor runs as a separate low-priority process.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import aiokafka
from sqlalchemy import text

from data_platform.adapters.eodhd_adapter import EODHDOHLCVRecord
from data_platform.quality.idx_data_validator import IDXInstrumentMetadata, IDXOHLCVValidator

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from shared.kafka_topics import KafkaTopic
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass
class DLQProcessingResult:
    """Result of processing a DLQ record."""

    disposition: str  # "retried", "resolved", "permanent"
    retry_count: int
    reason: str


class DLQProcessor:
    """Processes failed records from DLQ topics."""

    MAX_RETRIES = 3
    CONSUMER_GROUP = "pyhron-dlq-processor"

    def __init__(
        self,
        db_session: AsyncSession | None = None,
        kafka_bootstrap_servers: str = "localhost:9092",
    ) -> None:
        self._db_session = db_session
        self._bootstrap_servers = kafka_bootstrap_servers
        self._validator = IDXOHLCVValidator()
        self._consumer: aiokafka.AIOKafkaConsumer | None = None
        self._producer: aiokafka.AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start consumer and producer."""
        self._consumer = aiokafka.AIOKafkaConsumer(
            KafkaTopic.DLQ_EOD_OHLCV,
            KafkaTopic.DLQ_FUNDAMENTALS,
            KafkaTopic.DLQ_CORPORATE_ACTIONS,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self.CONSUMER_GROUP,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        self._producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self._consumer.start()
        await self._producer.start()

    async def stop(self) -> None:
        """Stop consumer and producer."""
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()

    async def run(self) -> None:
        """Main consumer loop."""
        if not self._consumer:
            raise RuntimeError("DLQ processor not started")

        async for msg in self._consumer:
            record = msg.value
            retry_count = record.get("retry_count", 0)

            result = await self.process_record(record, msg.topic, retry_count)

            if self._consumer:
                await self._consumer.commit()

            logger.info(
                "dlq_record_processed",
                topic=msg.topic,
                disposition=result.disposition,
                retry_count=result.retry_count,
            )

    async def process_record(
        self,
        record: dict[str, Any],
        topic: str,
        retry_count: int,
    ) -> DLQProcessingResult:
        """Attempt to re-process a failed record."""
        if retry_count >= self.MAX_RETRIES:
            await self._write_permanent(record, topic, retry_count)
            return DLQProcessingResult(
                disposition="permanent",
                retry_count=retry_count,
                reason=f"Max retries ({self.MAX_RETRIES}) exceeded",
            )

        # Try re-validation
        original = record.get("original_record", record)
        if topic == KafkaTopic.DLQ_EOD_OHLCV:
            try:
                ohlcv = EODHDOHLCVRecord(
                    symbol=original["symbol"],
                    date=date.fromisoformat(str(original["date"])),
                    open=Decimal(str(original["open"])),
                    high=Decimal(str(original["high"])),
                    low=Decimal(str(original["low"])),
                    close=Decimal(str(original["close"])),
                    adjusted_close=Decimal(str(original.get("adjusted_close", original["close"]))),
                    volume=int(original.get("volume", 0)),
                )
                instrument = IDXInstrumentMetadata(symbol=original["symbol"])
                prev_close = Decimal(str(original["prev_close"])) if original.get("prev_close") else None
                result = self._validator.validate(ohlcv, prev_close, instrument)

                if result.is_valid and self._producer:
                    output = original.copy()
                    output["retry_count"] = retry_count + 1
                    await self._producer.send(KafkaTopic.VALIDATED_EOD_OHLCV, output)
                    return DLQProcessingResult(
                        disposition="resolved",
                        retry_count=retry_count + 1,
                        reason="Re-validation succeeded",
                    )
            except (KeyError, ValueError):
                pass

        # Re-publish to DLQ with incremented retry count
        record["retry_count"] = retry_count + 1
        if self._producer:
            await self._producer.send(topic, record)

        return DLQProcessingResult(
            disposition="retried",
            retry_count=retry_count + 1,
            reason="Re-queued for retry",
        )

    async def _write_permanent(self, record: dict[str, Any], topic: str, retry_count: int) -> None:
        """Write permanently failed record to dlq_permanent table."""
        if not self._db_session:
            logger.error("dlq_permanent_write_skipped_no_session", topic=topic)
            return

        failure_reason = record.get("failure_reason", str(record.get("failed_rules", "unknown")))
        await self._db_session.execute(
            text(
                "INSERT INTO dlq_permanent (topic, payload, failure_reason, retry_count, "
                "first_failed_at, created_at) "
                "VALUES (:topic, :payload, :failure_reason, :retry_count, :first_failed_at, now())"
            ),
            {
                "topic": topic,
                "payload": json.dumps(record, default=str),
                "failure_reason": failure_reason,
                "retry_count": retry_count,
                "first_failed_at": datetime.now(UTC).isoformat(),
            },
        )
        await self._db_session.flush()
        logger.error(
            "dlq_record_permanent",
            topic=topic,
            retry_count=retry_count,
            failure_reason=failure_reason,
        )
