"""Intraday market data ingestion service.

Connects to Alpaca's real-time data WebSocket, receives trade/quote/bar
events, and publishes them to Kafka intraday topics for downstream
validation, persistence, and WebSocket fan-out.

Usage::

    service = IntradayIngestionService(symbols=["AAPL", "MSFT", "BBCA.JK"])
    await service.start()
    await service.run()  # runs until cancelled
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiokafka

from services.broker_connectivity.alpaca_broker_adapter import AlpacaBrokerAdapter
from shared.kafka_topics import KafkaTopic
from shared.metrics import intraday_events_total, intraday_publish_errors_total
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# Map event_type → Kafka topic
_EVENT_TOPIC_MAP: dict[str, str] = {
    "trade": KafkaTopic.RAW_INTRADAY_TRADES,
    "quote": KafkaTopic.RAW_INTRADAY_QUOTES,
    "bar": KafkaTopic.RAW_INTRADAY_BARS,
}


class IntradayIngestionService:
    """Streams real-time market data from Alpaca to Kafka.

    Subscribes to trades and minute bars via the Alpaca Data WebSocket
    (IEX feed) and publishes each event to the appropriate Kafka
    intraday topic with the symbol as the message key.
    """

    def __init__(
        self,
        symbols: list[str],
        bootstrap_servers: str = "localhost:9092",
        *,
        trades: bool = True,
        quotes: bool = False,
        bars: bool = True,
    ) -> None:
        self._symbols = symbols
        self._bootstrap_servers = bootstrap_servers
        self._trades = trades
        self._quotes = quotes
        self._bars = bars
        self._adapter = AlpacaBrokerAdapter()
        self._producer: aiokafka.AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Initialize the Kafka producer."""
        self._producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info(
            "intraday_ingestion_started",
            symbols=self._symbols,
            trades=self._trades,
            quotes=self._quotes,
            bars=self._bars,
        )

    async def stop(self) -> None:
        """Shut down the Kafka producer and broker adapter."""
        if self._producer:
            await self._producer.stop()
        await self._adapter.close()
        logger.info("intraday_ingestion_stopped")

    async def run(self) -> None:
        """Main loop: stream from Alpaca and publish to Kafka.

        Reconnects automatically on WebSocket disconnections via the
        adapter's built-in retry logic.
        """
        if not self._producer:
            raise RuntimeError("Service not started — call start() first")

        try:
            async for event in self._adapter.stream_market_data(
                self._symbols,
                trades=self._trades,
                quotes=self._quotes,
                bars=self._bars,
            ):
                await self._publish_event(event)
        except asyncio.CancelledError:
            logger.info("intraday_ingestion_cancelled")
        except Exception:
            logger.exception("intraday_ingestion_fatal_error")
            raise

    async def _publish_event(self, event: dict[str, Any]) -> None:
        """Publish a single market data event to the appropriate Kafka topic."""
        if not self._producer:
            return

        event_type = event.get("event_type", "")
        topic = _EVENT_TOPIC_MAP.get(event_type)
        if topic is None:
            logger.warning("intraday_unknown_event_type", event_type=event_type)
            return

        symbol = event.get("symbol", "")
        try:
            await self._producer.send(topic, value=event, key=symbol)
            intraday_events_total.labels(event_type=event_type, symbol=symbol).inc()
        except Exception:
            intraday_publish_errors_total.labels(topic=topic).inc()
            logger.exception(
                "intraday_kafka_publish_failed",
                topic=topic,
                symbol=symbol,
            )
