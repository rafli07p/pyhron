"""Integration tests for the intraday market data ingestion pipeline.

Tests the full flow: Alpaca WebSocket → IntradayIngestionService → Kafka topics,
validation consumer intraday bar validation, and Kafka→Redis bridge transforms.

Unit-testable components are tested with mocks; infrastructure-dependent tests
are marked @pytest.mark.integration and skipped without Kafka/Redis.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from data_platform.consumers.validation_consumer import ValidationConsumer
from services.api.websocket_gateway.kafka_redis_bridge import (
    MessageRouter,
    _transform_intraday_bar,
    _transform_intraday_trade,
)
from shared.kafka_topics import KafkaTopic

# Fixtures

SAMPLE_TRADE_EVENT = {
    "event_type": "trade",
    "symbol": "AAPL",
    "price": 185.50,
    "size": 100,
    "timestamp": "2024-03-01T14:30:00Z",
    "conditions": ["@"],
    "exchange": "V",
}

SAMPLE_BAR_EVENT = {
    "event_type": "bar",
    "symbol": "MSFT",
    "open": 410.0,
    "high": 412.5,
    "low": 409.8,
    "close": 411.3,
    "volume": 50000,
    "timestamp": "2024-03-01T14:31:00Z",
    "vwap": 411.1,
    "trade_count": 320,
}

SAMPLE_QUOTE_EVENT = {
    "event_type": "quote",
    "symbol": "GOOGL",
    "bid_price": 140.10,
    "bid_size": 200,
    "ask_price": 140.15,
    "ask_size": 150,
    "timestamp": "2024-03-01T14:30:05Z",
}


# 1. Event topic mapping


class TestEventTopicMapping:
    """Test that events route to the correct Kafka topics."""

    def test_trade_event_maps_to_raw_trades_topic(self) -> None:
        from data_platform.consumers.intraday_ingestion import _EVENT_TOPIC_MAP

        assert _EVENT_TOPIC_MAP["trade"] == KafkaTopic.RAW_INTRADAY_TRADES

    def test_bar_event_maps_to_raw_bars_topic(self) -> None:
        from data_platform.consumers.intraday_ingestion import _EVENT_TOPIC_MAP

        assert _EVENT_TOPIC_MAP["bar"] == KafkaTopic.RAW_INTRADAY_BARS

    def test_quote_event_maps_to_raw_quotes_topic(self) -> None:
        from data_platform.consumers.intraday_ingestion import _EVENT_TOPIC_MAP

        assert _EVENT_TOPIC_MAP["quote"] == KafkaTopic.RAW_INTRADAY_QUOTES

    def test_unknown_event_type_not_mapped(self) -> None:
        from data_platform.consumers.intraday_ingestion import _EVENT_TOPIC_MAP

        assert _EVENT_TOPIC_MAP.get("heartbeat") is None


# 2. IntradayIngestionService._publish_event


class TestPublishEvent:
    """Test event publishing to Kafka topics."""

    @pytest.mark.asyncio
    async def test_trade_published_to_correct_topic(self) -> None:
        from data_platform.consumers.intraday_ingestion import IntradayIngestionService

        with patch.object(IntradayIngestionService, "__init__", lambda self, **kw: None):
            service = IntradayIngestionService()  # type: ignore[call-arg]
            service._producer = AsyncMock()

            await service._publish_event(SAMPLE_TRADE_EVENT)

            service._producer.send.assert_called_once_with(
                KafkaTopic.RAW_INTRADAY_TRADES,
                value=SAMPLE_TRADE_EVENT,
                key="AAPL",
            )

    @pytest.mark.asyncio
    async def test_bar_published_to_correct_topic(self) -> None:
        from data_platform.consumers.intraday_ingestion import IntradayIngestionService

        with patch.object(IntradayIngestionService, "__init__", lambda self, **kw: None):
            service = IntradayIngestionService()  # type: ignore[call-arg]
            service._producer = AsyncMock()

            await service._publish_event(SAMPLE_BAR_EVENT)

            service._producer.send.assert_called_once_with(
                KafkaTopic.RAW_INTRADAY_BARS,
                value=SAMPLE_BAR_EVENT,
                key="MSFT",
            )

    @pytest.mark.asyncio
    async def test_unknown_event_type_not_published(self) -> None:
        from data_platform.consumers.intraday_ingestion import IntradayIngestionService

        with patch.object(IntradayIngestionService, "__init__", lambda self, **kw: None):
            service = IntradayIngestionService()  # type: ignore[call-arg]
            service._producer = AsyncMock()

            await service._publish_event({"event_type": "heartbeat", "symbol": "X"})

            service._producer.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_producer_is_noop(self) -> None:
        from data_platform.consumers.intraday_ingestion import IntradayIngestionService

        with patch.object(IntradayIngestionService, "__init__", lambda self, **kw: None):
            service = IntradayIngestionService()  # type: ignore[call-arg]
            service._producer = None

            # Should not raise
            await service._publish_event(SAMPLE_TRADE_EVENT)


# 3. Validation consumer — intraday bar validation


class TestIntradayBarValidation:
    """Test the validation consumer's intraday bar validator."""

    def _make_consumer(self) -> ValidationConsumer:
        return ValidationConsumer(bootstrap_servers="localhost:9092")

    def test_valid_bar_passes(self) -> None:
        consumer = self._make_consumer()
        result = consumer._validate_intraday_bar(SAMPLE_BAR_EVENT)
        assert result.is_valid
        assert result.failed_rules == []

    def test_missing_symbol_fails(self) -> None:
        consumer = self._make_consumer()
        bar = {**SAMPLE_BAR_EVENT, "symbol": ""}
        result = consumer._validate_intraday_bar(bar)
        assert not result.is_valid
        assert "MISSING_SYMBOL" in result.failed_rules

    def test_missing_timestamp_fails(self) -> None:
        consumer = self._make_consumer()
        bar = {**SAMPLE_BAR_EVENT, "timestamp": ""}
        result = consumer._validate_intraday_bar(bar)
        assert not result.is_valid
        assert "MISSING_TIMESTAMP" in result.failed_rules

    def test_high_less_than_low_fails(self) -> None:
        consumer = self._make_consumer()
        bar = {**SAMPLE_BAR_EVENT, "high": 400.0, "low": 420.0}
        result = consumer._validate_intraday_bar(bar)
        assert not result.is_valid
        assert "HIGH_LESS_THAN_LOW" in result.failed_rules

    def test_negative_price_fails(self) -> None:
        consumer = self._make_consumer()
        bar = {**SAMPLE_BAR_EVENT, "open": -1.0}
        result = consumer._validate_intraday_bar(bar)
        assert not result.is_valid
        assert "NEGATIVE_PRICE" in result.failed_rules

    def test_negative_volume_fails(self) -> None:
        consumer = self._make_consumer()
        bar = {**SAMPLE_BAR_EVENT, "volume": -100}
        result = consumer._validate_intraday_bar(bar)
        assert not result.is_valid
        assert "NEGATIVE_VOLUME" in result.failed_rules

    def test_zero_prices_pass(self) -> None:
        consumer = self._make_consumer()
        bar = {**SAMPLE_BAR_EVENT, "open": 0, "high": 0, "low": 0, "close": 0}
        result = consumer._validate_intraday_bar(bar)
        assert result.is_valid


# 4. Kafka→Redis bridge — message routing


class TestIntradayMessageRouting:
    """Test that intraday events route to correct Redis channels."""

    def test_trade_routes_to_intraday_channel(self) -> None:
        router = MessageRouter()
        channel = router.route(KafkaTopic.RAW_INTRADAY_TRADES, {"symbol": "AAPL"})
        assert channel == "pyhron:intraday:AAPL"

    def test_bar_routes_to_intraday_channel(self) -> None:
        router = MessageRouter()
        channel = router.route(KafkaTopic.RAW_INTRADAY_BARS, {"symbol": "MSFT"})
        assert channel == "pyhron:intraday:MSFT"

    def test_missing_symbol_returns_none(self) -> None:
        router = MessageRouter()
        channel = router.route(KafkaTopic.RAW_INTRADAY_TRADES, {})
        assert channel is None

    def test_unknown_topic_returns_none(self) -> None:
        router = MessageRouter()
        channel = router.route("pyhron.unknown.topic", {"symbol": "X"})
        assert channel is None


# 5. Kafka→Redis bridge — message transforms


class TestIntradayMessageTransforms:
    """Test WebSocket message transforms for intraday data."""

    def test_trade_transform(self) -> None:
        result = _transform_intraday_trade(SAMPLE_TRADE_EVENT)
        assert result["type"] == "TRADE_UPDATE"
        assert result["symbol"] == "AAPL"
        assert result["price"] == "185.5"
        assert result["size"] == 100
        assert result["timestamp"] == "2024-03-01T14:30:00Z"

    def test_bar_transform(self) -> None:
        result = _transform_intraday_bar(SAMPLE_BAR_EVENT)
        assert result["type"] == "BAR_UPDATE"
        assert result["symbol"] == "MSFT"
        assert result["open"] == "410.0"
        assert result["high"] == "412.5"
        assert result["low"] == "409.8"
        assert result["close"] == "411.3"
        assert result["volume"] == 50000
        assert result["vwap"] == "411.1"
        assert result["trade_count"] == 320

    def test_trade_transform_missing_fields_default(self) -> None:
        result = _transform_intraday_trade({})
        assert result["type"] == "TRADE_UPDATE"
        assert result["symbol"] == ""
        assert result["price"] == ""
        assert result["size"] == 0

    def test_bar_transform_missing_fields_default(self) -> None:
        result = _transform_intraday_bar({})
        assert result["type"] == "BAR_UPDATE"
        assert result["symbol"] == ""
        assert result["volume"] == 0
        assert result["trade_count"] == 0


# 6. Kafka topic routing table


class TestIntradayTopicRouting:
    """Test that intraday topics are correctly wired into the validation consumer."""

    def test_intraday_bars_in_topic_routing(self) -> None:
        from data_platform.consumers.validation_consumer import _TOPIC_ROUTING

        assert KafkaTopic.RAW_INTRADAY_BARS in _TOPIC_ROUTING
        validated, dlq = _TOPIC_ROUTING[KafkaTopic.RAW_INTRADAY_BARS]
        assert validated == KafkaTopic.VALIDATED_INTRADAY_BARS
        assert dlq == KafkaTopic.DLQ_INTRADAY

    def test_intraday_topics_in_bridge_list(self) -> None:
        from services.api.main import _TOPICS_TO_BRIDGE

        assert KafkaTopic.RAW_INTRADAY_TRADES in _TOPICS_TO_BRIDGE
        assert KafkaTopic.RAW_INTRADAY_BARS in _TOPICS_TO_BRIDGE


# 7. Full pipeline integration (requires infrastructure)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alpaca_to_kafka_to_redis_pipeline() -> None:
    """End-to-end: mock Alpaca WebSocket → IntradayIngestionService → Kafka
    → validation consumer → validated topic → Kafka→Redis bridge → Redis channel.
    """
    pytest.skip("Requires full infrastructure (Kafka, Redis, Alpaca)")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_intraday_bar_persists_to_timescaledb() -> None:
    """Validated intraday bar → TimescaleDB writer → ohlcv table with IEX exchange."""
    pytest.skip("Requires full infrastructure (Kafka, TimescaleDB)")
