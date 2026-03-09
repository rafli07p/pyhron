"""Publish strategy signals to Kafka for downstream consumption.

Bridges the strategy engine output to the live execution pipeline by
serialising ``StrategySignal`` objects into Protobuf and publishing
them to the ``pyhron.equity.strategy-signals`` Kafka topic.

Usage::

    async with StrategySignalPublisher(kafka_servers="kafka:29092") as pub:
        await pub.publish_signals(signals)
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from shared.kafka_producer_consumer import PyhronProducer, Topics
from shared.structured_json_logger import get_logger
from shared.prometheus_metrics_registry import ORDERS_TOTAL
from strategy_engine.base_strategy_interface import StrategySignal

logger = get_logger(__name__)


class StrategySignalPublisher:
    """Publish strategy signals to Kafka for live execution.

    Each signal is serialised as a JSON-encoded byte payload and sent
    to the equity strategy signals topic.  The partition key is the
    ``strategy_id`` for consistent routing.

    Args:
        kafka_servers: Kafka bootstrap servers.
        topic: Target Kafka topic (default: equity strategy signals).
    """

    def __init__(
        self,
        kafka_servers: str = "kafka:29092",
        topic: str = Topics.EQUITY_STRATEGY_SIGNALS,
    ) -> None:
        self._kafka_servers = kafka_servers
        self._topic = topic
        self._producer: PyhronProducer | None = None

        logger.info(
            "signal_publisher_initialised",
            kafka_servers=kafka_servers,
            topic=topic,
        )

    async def start(self) -> None:
        """Start the underlying Kafka producer."""
        self._producer = PyhronProducer(self._kafka_servers)
        await self._producer.start()
        logger.info("signal_publisher_started")

    async def stop(self) -> None:
        """Stop the Kafka producer and flush pending messages."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
        logger.info("signal_publisher_stopped")

    async def __aenter__(self) -> StrategySignalPublisher:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    async def publish_signals(self, signals: list[StrategySignal]) -> int:
        """Publish a batch of strategy signals to Kafka.

        Args:
            signals: List of StrategySignal to publish.

        Returns:
            Number of signals successfully published.
        """
        if self._producer is None:
            raise RuntimeError("Publisher not started — call start() or use async with")

        published = 0
        for signal in signals:
            payload = self._serialise_signal(signal)
            try:
                await self._producer._producer.send_and_wait(
                    self._topic,
                    value=json.dumps(payload).encode("utf-8"),
                    key=signal.strategy_id.encode("utf-8"),
                )
                published += 1
                logger.debug(
                    "signal_published",
                    symbol=signal.symbol,
                    direction=signal.direction.value,
                    strategy_id=signal.strategy_id,
                )
            except Exception as exc:
                logger.error(
                    "signal_publish_failed",
                    symbol=signal.symbol,
                    error=str(exc),
                )

        logger.info(
            "signal_batch_published",
            total=len(signals),
            published=published,
            failed=len(signals) - published,
        )
        return published

    @staticmethod
    def _serialise_signal(signal: StrategySignal) -> dict[str, Any]:
        """Convert a StrategySignal to a JSON-serialisable dictionary.

        Args:
            signal: Strategy signal to serialise.

        Returns:
            Dictionary representation of the signal.
        """
        return {
            "symbol": signal.symbol,
            "direction": signal.direction.value,
            "target_weight": signal.target_weight,
            "confidence": signal.confidence,
            "strategy_id": signal.strategy_id,
            "generated_at": signal.generated_at.isoformat(),
            "metadata": signal.metadata,
        }
