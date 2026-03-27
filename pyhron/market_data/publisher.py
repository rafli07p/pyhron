"""Kafka-based market data publisher for the Pyhron trading platform.

Publishes tick data to a Kafka topic for downstream consumers
(paper trading, research, monitoring).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pyhron.shared.schemas.tick import TickData

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    success: bool
    partition: int | None
    offset: int | None


class MarketDataPublisher:
    """Async Kafka publisher for market data ticks.

    Parameters
    ----------
    bootstrap_servers:
        Kafka bootstrap servers (e.g. ``localhost:9092``).
    topic:
        Kafka topic to publish to.
    """

    def __init__(self, bootstrap_servers: str, topic: str = "pyhron.market_data.ticks") -> None:
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self._producer = None

    async def connect(self) -> None:
        """Start the Kafka producer."""
        from aiokafka import AIOKafkaProducer

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info("market_data_publisher.connected", extra={"servers": self.bootstrap_servers})

    async def disconnect(self) -> None:
        """Stop the Kafka producer gracefully."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("market_data_publisher.disconnected")

    async def publish_tick(self, tick: TickData) -> PublishResult:
        """Publish a single tick to Kafka.

        The tick symbol is used as the message key for partition affinity.
        """
        if self._producer is None:
            raise RuntimeError("Publisher not connected")

        payload = {
            "symbol": tick.symbol,
            "price": str(tick.price),
            "volume": tick.volume,
            "bid": str(tick.bid),
            "ask": str(tick.ask),
            "timestamp": tick.timestamp.isoformat(),
            "exchange": tick.exchange,
        }

        try:
            record = await self._producer.send_and_wait(
                self.topic,
                value=payload,
                key=tick.symbol,
            )
            return PublishResult(
                success=True,
                partition=record.partition,
                offset=record.offset,
            )
        except Exception:
            logger.exception("market_data_publisher.publish_failed", extra={"symbol": tick.symbol})
            return PublishResult(success=False, partition=None, offset=None)

    async def publish_batch(self, ticks: list[TickData]) -> list[PublishResult]:
        """Publish multiple ticks. Returns results in the same order."""
        results: list[PublishResult] = []
        for tick in ticks:
            result = await self.publish_tick(tick)
            results.append(result)
        return results
