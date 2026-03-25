"""Kafka consumer that reads from raw topics, validates records, and routes.

Consumer group: pyhron-validation-consumer

For each record:
1. Deserialize from JSON
2. Run appropriate validator
3. If valid: publish to validated topic
4. If invalid with warnings: publish to validated topic with warnings
5. If invalid (hard failure): publish to DLQ with failure reason
6. Commit offset after routing decision is made
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

import aiokafka

from data_platform.adapters.eodhd_adapter import EODHDOHLCVRecord
from data_platform.quality.idx_data_validator import (
    IDXFundamentalsValidator,
    IDXInstrumentMetadata,
    IDXOHLCVValidator,
    ValidationResult,
)
from shared.kafka_topics import KafkaTopic
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

_TOPIC_ROUTING: dict[str, tuple[str, str]] = {
    KafkaTopic.RAW_EOD_OHLCV: (KafkaTopic.VALIDATED_EOD_OHLCV, KafkaTopic.DLQ_EOD_OHLCV),
    KafkaTopic.RAW_FUNDAMENTALS: (KafkaTopic.VALIDATED_FUNDAMENTALS, KafkaTopic.DLQ_FUNDAMENTALS),
    KafkaTopic.RAW_INTRADAY_BARS: (KafkaTopic.VALIDATED_INTRADAY_BARS, KafkaTopic.DLQ_INTRADAY),
}


class ValidationConsumer:
    """Kafka consumer that validates raw records and routes them."""

    CONSUMER_GROUP = "pyhron-validation-consumer"

    def __init__(
        self,
        bootstrap_servers: str,
        ohlcv_validator: IDXOHLCVValidator | None = None,
        fundamentals_validator: IDXFundamentalsValidator | None = None,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._ohlcv_validator = ohlcv_validator or IDXOHLCVValidator()
        self._fundamentals_validator = fundamentals_validator or IDXFundamentalsValidator()
        self._consumer: aiokafka.AIOKafkaConsumer | None = None
        self._producer: aiokafka.AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start consumer and producer."""
        self._consumer = aiokafka.AIOKafkaConsumer(
            KafkaTopic.RAW_EOD_OHLCV,
            KafkaTopic.RAW_FUNDAMENTALS,
            KafkaTopic.RAW_INTRADAY_BARS,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self.CONSUMER_GROUP,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        self._producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self._consumer.start()
        await self._producer.start()
        logger.info("validation_consumer_started")

    async def stop(self) -> None:
        """Stop consumer and producer."""
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()
        logger.info("validation_consumer_stopped")

    async def run(self) -> None:
        """Main consumer loop. Runs until cancellation."""
        if not self._consumer or not self._producer:
            raise RuntimeError("Consumer not started")

        async for msg in self._consumer:
            try:
                await self._process_message(msg)
                await self._consumer.commit()
            except Exception as e:
                logger.error("validation_consumer_error", error=str(e), topic=msg.topic)

    async def _process_message(self, msg: aiokafka.ConsumerRecord) -> None:
        """Process a single message: validate and route."""
        if not self._producer:
            return

        routing = _TOPIC_ROUTING.get(msg.topic)
        if not routing:
            logger.warning("unknown_raw_topic", topic=msg.topic)
            return

        validated_topic, dlq_topic = routing
        record_data = msg.value

        if msg.topic == KafkaTopic.RAW_EOD_OHLCV:
            result = self._validate_ohlcv(record_data)
        elif msg.topic == KafkaTopic.RAW_FUNDAMENTALS:
            result = self._validate_fundamentals(record_data)
        elif msg.topic == KafkaTopic.RAW_INTRADAY_BARS:
            result = self._validate_intraday_bar(record_data)
        else:
            await self._producer.send(validated_topic, record_data)
            return

        if result.is_valid:
            output = record_data.copy()
            if result.warnings:
                output["_warnings"] = result.warnings
            if result.adjusted_record:
                output["close"] = str(result.adjusted_record.close)
            await self._producer.send(validated_topic, output)
        else:
            dlq_record = {
                "original_record": record_data,
                "failed_rules": result.failed_rules,
                "warnings": result.warnings,
                "source_topic": msg.topic,
            }
            await self._producer.send(dlq_topic, dlq_record)
            logger.warning(
                "record_sent_to_dlq",
                topic=dlq_topic,
                failed_rules=result.failed_rules,
                symbol=record_data.get("symbol"),
            )

    def _validate_ohlcv(self, data: dict[str, Any]) -> ValidationResult:
        from data_platform.quality.idx_data_validator import ValidationResult

        try:
            record = EODHDOHLCVRecord(
                symbol=data["symbol"],
                date=date.fromisoformat(str(data["date"])),
                open=Decimal(str(data["open"])),
                high=Decimal(str(data["high"])),
                low=Decimal(str(data["low"])),
                close=Decimal(str(data["close"])),
                adjusted_close=Decimal(str(data.get("adjusted_close", data["close"]))),
                volume=int(data.get("volume", 0)),
                source=data.get("source", "unknown"),
            )
            prev_close = Decimal(str(data["prev_close"])) if data.get("prev_close") else None
            instrument = IDXInstrumentMetadata(
                symbol=data["symbol"],
                avg_daily_volume=int(data.get("avg_daily_volume", 0)),
            )
            return self._ohlcv_validator.validate(record, prev_close, instrument)
        except (KeyError, ValueError) as e:
            dummy = EODHDOHLCVRecord(
                symbol=data.get("symbol", "UNKNOWN"),
                date=date.today(),
                open=Decimal("0"),
                high=Decimal("0"),
                low=Decimal("0"),
                close=Decimal("0"),
                adjusted_close=Decimal("0"),
                volume=0,
            )
            return ValidationResult(
                is_valid=False,
                record=dummy,
                failed_rules=[f"PARSE_ERROR: {e}"],
            )

    def _validate_fundamentals(self, data: dict[str, Any]) -> ValidationResult:
        return self._fundamentals_validator.validate(data, data.get("symbol", "UNKNOWN"))

    def _validate_intraday_bar(self, data: dict[str, Any]) -> ValidationResult:
        """Basic validation for intraday bar data from Alpaca."""
        failed_rules: list[str] = []
        warnings: list[str] = []

        if not data.get("symbol"):
            failed_rules.append("MISSING_SYMBOL")
        if not data.get("timestamp"):
            failed_rules.append("MISSING_TIMESTAMP")

        high = float(data.get("high", 0))
        low = float(data.get("low", 0))
        open_price = float(data.get("open", 0))
        close = float(data.get("close", 0))

        if high < low and high > 0:
            failed_rules.append("HIGH_LESS_THAN_LOW")
        if any(v < 0 for v in (open_price, high, low, close)):
            failed_rules.append("NEGATIVE_PRICE")
        if int(data.get("volume", 0)) < 0:
            failed_rules.append("NEGATIVE_VOLUME")

        # Create a dummy record for ValidationResult compatibility
        dummy = EODHDOHLCVRecord(
            symbol=data.get("symbol", "UNKNOWN"),
            date=date.today(),
            open=Decimal(str(open_price)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
            adjusted_close=Decimal(str(close)),
            volume=int(data.get("volume", 0)),
        )

        return ValidationResult(
            is_valid=len(failed_rules) == 0,
            record=dummy,
            failed_rules=failed_rules,
            warnings=warnings,
        )
