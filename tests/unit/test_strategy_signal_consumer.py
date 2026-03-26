"""Unit tests for StrategySignalKafkaConsumer."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.paper_trading.strategy_executor import RebalanceResult
from services.paper_trading.strategy_signal_consumer import (
    ConsumerHealthStatus,
    StrategySignalKafkaConsumer,
)


class TestStrategySignalConsumer:
    """Tests for StrategySignalKafkaConsumer initialization and lifecycle."""

    def test_default_construction(self):
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="localhost:9092")
            consumer = StrategySignalKafkaConsumer()
            assert consumer._bootstrap_servers == "localhost:9092"
            assert consumer._batch_size == 50
            assert consumer._batch_timeout_s == 5.0
            assert consumer._running is False

    def test_custom_batch_settings(self):
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="kafka:29092")
            consumer = StrategySignalKafkaConsumer(batch_size=10, batch_timeout_s=2.0)
            assert consumer._batch_size == 10
            assert consumer._batch_timeout_s == 2.0

    def test_custom_executor(self):
        mock_executor = MagicMock()
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="localhost:9092")
            consumer = StrategySignalKafkaConsumer(executor=mock_executor)
            assert consumer._executor is mock_executor


class TestExtractLastPrices:
    """Tests for price extraction from signal payloads."""

    def _make_consumer(self) -> StrategySignalKafkaConsumer:
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="localhost:9092")
            return StrategySignalKafkaConsumer()

    def test_extract_prices_from_signals(self):
        consumer = self._make_consumer()
        signals = [
            {"symbol": "BBCA", "last_price": "9250", "target_weight": "0.15"},
            {"symbol": "BBRI", "last_price": "5400", "target_weight": "0.10"},
        ]
        prices = consumer._extract_last_prices(signals)
        assert prices == {"BBCA": Decimal("9250"), "BBRI": Decimal("5400")}

    def test_empty_signals(self):
        consumer = self._make_consumer()
        prices = consumer._extract_last_prices([])
        assert prices == {}

    def test_missing_price_field(self):
        consumer = self._make_consumer()
        signals = [{"symbol": "BBCA", "target_weight": "0.15"}]
        prices = consumer._extract_last_prices(signals)
        assert prices == {}

    def test_invalid_price_value(self):
        consumer = self._make_consumer()
        signals = [{"symbol": "BBCA", "last_price": "not-a-number"}]
        prices = consumer._extract_last_prices(signals)
        assert prices == {}

    def test_duplicate_symbol_uses_latest(self):
        consumer = self._make_consumer()
        signals = [
            {"symbol": "BBCA", "last_price": "9200"},
            {"symbol": "BBCA", "last_price": "9300"},
        ]
        prices = consumer._extract_last_prices(signals)
        assert prices["BBCA"] == Decimal("9300")


class TestPublishResult:
    """Tests for publishing rebalance results to Kafka."""

    @pytest.fixture()
    def consumer_with_producer(self):
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="localhost:9092")
            consumer = StrategySignalKafkaConsumer()
            consumer._producer = AsyncMock()
            return consumer

    async def test_publish_result_sends_to_kafka(self, consumer_with_producer):
        consumer = consumer_with_producer
        result = RebalanceResult(
            session_id="session-123",
            rebalance_at=datetime(2025, 1, 15, 9, 30, tzinfo=UTC),
            signals_consumed=5,
            orders_submitted=3,
            orders_rejected=1,
            estimated_turnover_idr=Decimal("150000000"),
            instructions=[],
        )
        await consumer._publish_result(result)
        consumer._producer.send_and_wait.assert_awaited_once()
        call_kwargs = consumer._producer.send_and_wait.call_args
        assert call_kwargs[1]["key"] == "session-123"

    async def test_publish_result_no_producer(self):
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="localhost:9092")
            consumer = StrategySignalKafkaConsumer()
            consumer._producer = None
            result = RebalanceResult(
                session_id="session-123",
                rebalance_at=datetime(2025, 1, 15, 9, 30, tzinfo=UTC),
                signals_consumed=0,
                orders_submitted=0,
                orders_rejected=0,
                estimated_turnover_idr=Decimal("0"),
            )
            # Should not raise
            await consumer._publish_result(result)


class TestFlushBuffer:
    """Tests for buffer flushing logic."""

    async def test_flush_calls_execute_for_each_session(self):
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="localhost:9092")
            consumer = StrategySignalKafkaConsumer()
            consumer._producer = AsyncMock()

            mock_result = RebalanceResult(
                session_id="s1",
                rebalance_at=datetime.now(UTC),
                signals_consumed=2,
                orders_submitted=1,
                orders_rejected=0,
                estimated_turnover_idr=Decimal("100000000"),
            )

            with patch.object(consumer, "_execute_rebalance", new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = mock_result
                buffer: dict[str, list[dict[str, Any]]] = {
                    "session-1": [{"symbol": "BBCA", "session_id": "session-1"}],
                    "session-2": [{"symbol": "BBRI", "session_id": "session-2"}],
                }
                await consumer._flush_buffer(buffer)
                assert mock_exec.await_count == 2

    async def test_flush_handles_execution_error(self):
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="localhost:9092")
            consumer = StrategySignalKafkaConsumer()
            consumer._producer = AsyncMock()

            with patch.object(consumer, "_execute_rebalance", new_callable=AsyncMock) as mock_exec:
                mock_exec.side_effect = RuntimeError("DB error")
                buffer: dict[str, list[dict[str, Any]]] = {
                    "session-1": [{"symbol": "BBCA"}],
                }
                # Should not raise — errors are logged
                await consumer._flush_buffer(buffer)


class TestRunNotStarted:
    """Test that run() raises if not started."""

    async def test_run_raises_without_start(self):
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="localhost:9092")
            consumer = StrategySignalKafkaConsumer()
            with pytest.raises(RuntimeError, match="Consumer not started"):
                await consumer.run()


class TestConsumerHealthStatus:
    """Tests for ConsumerHealthStatus dataclass."""

    def test_stopped_status(self):
        status = ConsumerHealthStatus(running=False)
        assert status.status == "stopped"

    def test_healthy_status(self):
        status = ConsumerHealthStatus(running=True, messages_processed=100, errors=5)
        assert status.status == "healthy"

    def test_degraded_status_high_error_rate(self):
        status = ConsumerHealthStatus(running=True, messages_processed=100, errors=15)
        assert status.status == "degraded"

    def test_healthy_with_zero_messages(self):
        status = ConsumerHealthStatus(running=True, messages_processed=0, errors=0)
        assert status.status == "healthy"


class TestConsumerHealth:
    """Tests for the consumer health() method."""

    def _make_consumer(self) -> StrategySignalKafkaConsumer:
        with patch("services.paper_trading.strategy_signal_consumer.get_config") as mock_config:
            mock_config.return_value = MagicMock(kafka_bootstrap_servers="localhost:9092")
            return StrategySignalKafkaConsumer()

    def test_health_when_stopped(self):
        consumer = self._make_consumer()
        health = consumer.health()
        assert health.status == "stopped"
        assert health.running is False
        assert health.started_at is None
        assert health.messages_processed == 0

    def test_health_reports_topics(self):
        consumer = self._make_consumer()
        health = consumer.health()
        assert len(health.topics) == 2
        assert health.consumer_group == "paper-strategy-executor"

    def test_health_tracks_counters(self):
        consumer = self._make_consumer()
        consumer._running = True
        consumer._started_at = datetime(2025, 1, 15, 9, 0, tzinfo=UTC)
        consumer._messages_processed = 42
        consumer._batches_flushed = 3
        consumer._errors = 1
        consumer._last_message_at = datetime(2025, 1, 15, 9, 30, tzinfo=UTC)
        health = consumer.health()
        assert health.status == "healthy"
        assert health.messages_processed == 42
        assert health.batches_flushed == 3
        assert health.errors == 1
        assert health.last_message_at == datetime(2025, 1, 15, 9, 30, tzinfo=UTC)
