"""Kafka consumer that writes validated records to TimescaleDB.

Consumer group: pyhron-timescaledb-writer
Topics consumed:
  pyhron.validated.eod_ohlcv
  pyhron.validated.fundamentals

Write strategy:
- Batch records in memory for up to 500ms or 1000 records
- Execute bulk upsert using INSERT ... ON CONFLICT DO NOTHING
- Commit Kafka offset ONLY after successful DB commit
- On DB failure: do not commit offset (record will be redelivered)

This implements at-least-once delivery with idempotent writes.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

import aiokafka
from sqlalchemy import text

from shared.kafka_topics import KafkaTopic

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class TimescaleDBWriterConsumer:
    """Kafka consumer that writes validated records to TimescaleDB."""

    CONSUMER_GROUP = "pyhron-timescaledb-writer"
    BATCH_SIZE = 1000
    BATCH_TIMEOUT_MS = 500

    def __init__(
        self,
        bootstrap_servers: str,
        db_session_factory: object,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._db_session_factory = db_session_factory
        self._consumer: aiokafka.AIOKafkaConsumer | None = None
        self._dlq_producer: aiokafka.AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start consumer and DLQ producer."""
        self._consumer = aiokafka.AIOKafkaConsumer(
            KafkaTopic.VALIDATED_EOD_OHLCV,
            KafkaTopic.VALIDATED_FUNDAMENTALS,
            KafkaTopic.VALIDATED_INTRADAY_BARS,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self.CONSUMER_GROUP,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            max_poll_records=self.BATCH_SIZE,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        self._dlq_producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            acks="all",
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self._consumer.start()
        await self._dlq_producer.start()
        logger.info("timescaledb_writer_started")

    async def stop(self) -> None:
        """Stop consumer and DLQ producer."""
        if self._consumer:
            await self._consumer.stop()
        if self._dlq_producer:
            await self._dlq_producer.stop()
        logger.info("timescaledb_writer_stopped")

    async def run(self) -> None:
        """Main consumer loop. Runs until cancellation."""
        if not self._consumer:
            raise RuntimeError("Consumer not started")

        batch: list[tuple[str, dict[str, Any]]] = []
        batch_start = time.monotonic()

        async for msg in self._consumer:
            batch.append((msg.topic, msg.value))

            elapsed_ms = (time.monotonic() - batch_start) * 1000
            if len(batch) >= self.BATCH_SIZE or elapsed_ms >= self.BATCH_TIMEOUT_MS:
                await self._process_batch(batch)
                batch = []
                batch_start = time.monotonic()

    async def _process_batch(self, batch: list[tuple[str, dict[str, Any]]]) -> None:
        """Process a batch of messages."""
        if not batch or not self._consumer:
            return

        ohlcv_records = [r for t, r in batch if t == KafkaTopic.VALIDATED_EOD_OHLCV]
        fundamental_records = [r for t, r in batch if t == KafkaTopic.VALIDATED_FUNDAMENTALS]
        intraday_records = [r for t, r in batch if t == KafkaTopic.VALIDATED_INTRADAY_BARS]

        try:
            async with self._db_session_factory() as db_session:  # type: ignore[operator]
                written = 0
                if ohlcv_records:
                    written += await self._write_ohlcv_batch(ohlcv_records, db_session)
                if fundamental_records:
                    written += await self._write_fundamentals_batch(fundamental_records, db_session)
                if intraday_records:
                    written += await self._write_intraday_batch(intraday_records, db_session)
                await db_session.commit()

            # Commit Kafka offset ONLY after successful DB commit
            await self._consumer.commit()
            logger.info(
                "batch_written",
                ohlcv=len(ohlcv_records),
                fundamentals=len(fundamental_records),
                intraday=len(intraday_records),
                written=written,
            )
        except Exception as e:
            logger.error("batch_write_failed", error=str(e), batch_size=len(batch))
            # Do not commit offset — records will be redelivered
            for _, record in batch:
                await self._send_to_dlq(record, str(e), "batch_write_failure")

    async def _write_ohlcv_batch(
        self,
        records: list[dict[str, Any]],
        db_session: AsyncSession,
    ) -> int:
        """Bulk upsert OHLCV records using INSERT ... ON CONFLICT DO NOTHING."""
        if not records:
            return 0

        values_clauses = []
        params: dict[str, object] = {}
        for i, rec in enumerate(records):
            values_clauses.append(
                f"(:time_{i}, :symbol_{i}, :exchange_{i}, :open_{i}, :high_{i}, "
                f":low_{i}, :close_{i}, :volume_{i}, :adjusted_close_{i})"
            )
            params[f"time_{i}"] = rec.get("date", rec.get("time"))
            params[f"symbol_{i}"] = rec["symbol"]
            params[f"exchange_{i}"] = rec.get("exchange", "IDX")
            params[f"open_{i}"] = rec["open"]
            params[f"high_{i}"] = rec["high"]
            params[f"low_{i}"] = rec["low"]
            params[f"close_{i}"] = rec["close"]
            params[f"volume_{i}"] = rec.get("volume", 0)
            params[f"adjusted_close_{i}"] = rec.get("adjusted_close", rec["close"])

        sql = (
            "INSERT INTO ohlcv (time, symbol, exchange, open, high, low, close, volume, adjusted_close) "  # noqa: S608
            f"VALUES {', '.join(values_clauses)} "
            "ON CONFLICT (time, symbol, exchange) DO NOTHING"
        )
        result = await db_session.execute(text(sql), params)
        return result.rowcount  # type: ignore[no-any-return, attr-defined]

    async def _write_fundamentals_batch(
        self,
        records: list[dict[str, Any]],
        db_session: AsyncSession,
    ) -> int:
        """Bulk upsert fundamental records."""
        if not records:
            return 0

        written = 0
        for rec in records:
            sql = text(
                "INSERT INTO financial_statements (id, symbol, period_end, statement_type, revenue, net_income, "
                "total_assets, total_liabilities, total_equity, created_at) "
                "VALUES (gen_random_uuid(), :symbol, :period_end, :statement_type, :revenue, :net_income, "
                ":total_assets, :total_liabilities, :total_equity, now()) "
                "ON CONFLICT (symbol, period_end, statement_type) DO NOTHING"
            )
            result = await db_session.execute(
                sql,
                {
                    "symbol": rec.get("symbol"),
                    "period_end": rec.get("period_end", rec.get("fiscal_date")),
                    "statement_type": rec.get("statement_type", "INCOME"),
                    "revenue": rec.get("revenue"),
                    "net_income": rec.get("net_income"),
                    "total_assets": rec.get("total_assets"),
                    "total_liabilities": rec.get("total_liabilities"),
                    "total_equity": rec.get("total_equity"),
                },
            )
            written += result.rowcount  # type: ignore[attr-defined]
        return written

    async def _write_intraday_batch(
        self,
        records: list[dict[str, Any]],
        db_session: AsyncSession,
    ) -> int:
        """Bulk upsert intraday bar records using INSERT ... ON CONFLICT DO NOTHING."""
        if not records:
            return 0

        values_clauses = []
        params: dict[str, object] = {}
        for i, rec in enumerate(records):
            values_clauses.append(
                f"(:time_{i}, :symbol_{i}, :exchange_{i}, :open_{i}, :high_{i}, "
                f":low_{i}, :close_{i}, :volume_{i}, :adjusted_close_{i})"
            )
            params[f"time_{i}"] = rec.get("timestamp", rec.get("time"))
            params[f"symbol_{i}"] = rec["symbol"]
            params[f"exchange_{i}"] = rec.get("exchange", "IEX")
            params[f"open_{i}"] = rec["open"]
            params[f"high_{i}"] = rec["high"]
            params[f"low_{i}"] = rec["low"]
            params[f"close_{i}"] = rec["close"]
            params[f"volume_{i}"] = rec.get("volume", 0)
            params[f"adjusted_close_{i}"] = rec.get("close")

        sql = (
            "INSERT INTO ohlcv (time, symbol, exchange, open, high, low, close, volume, adjusted_close) "  # noqa: S608
            f"VALUES {', '.join(values_clauses)} "
            "ON CONFLICT (time, symbol, exchange) DO NOTHING"
        )
        result = await db_session.execute(text(sql), params)
        return result.rowcount  # type: ignore[no-any-return, attr-defined]

    async def _send_to_dlq(
        self,
        record: dict[str, Any],
        reason: str,
        original_topic: str,
    ) -> None:
        """Send failed record to the appropriate DLQ topic."""
        if not self._dlq_producer:
            return

        dlq_topic = KafkaTopic.DLQ_EOD_OHLCV
        dlq_record = {
            "original_record": record,
            "failure_reason": reason,
            "source_topic": original_topic,
        }
        try:
            await self._dlq_producer.send(dlq_topic, dlq_record)
        except Exception as e:
            logger.error("dlq_send_failed", error=str(e))
