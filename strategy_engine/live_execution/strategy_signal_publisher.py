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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from shared.kafka_producer_consumer import PyhronProducer, Topics
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from datetime import date

    import pandas as pd

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
                if self._producer._producer is None:
                    raise RuntimeError("Kafka producer not initialized")
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
        """Convert a StrategySignal to a JSON-serialisable dictionary."""
        return {
            "symbol": signal.symbol,
            "direction": signal.direction.value,
            "target_weight": signal.target_weight,
            "confidence": signal.confidence,
            "strategy_id": signal.strategy_id,
            "generated_at": signal.generated_at.isoformat(),
            "metadata": signal.metadata,
        }


async def publish_momentum_signals(
    signals: pd.DataFrame,
    strategy_id: str,
    rebalance_date: date,
    kafka_producer: PyhronProducer,
) -> int:
    """Publish momentum signals to Kafka.

    Publishes to topic ``pyhron.strategy.signals.momentum`` in order:
      1. EXIT_LONG signals first (stocks leaving portfolio)
      2. ENTRY_LONG signals second (stocks entering portfolio)
      3. HOLD signals last

    This ordering allows the OMS to process sells before buys,
    preventing temporary capital shortfalls during rebalancing.

    Parameters
    ----------
    signals:
        Output from ``generate_signals_full()``.
    strategy_id:
        Strategy identifier.
    rebalance_date:
        The rebalance date for these signals.
    kafka_producer:
        Active PyhronProducer instance.

    Returns
    -------
    int
        Number of signals published.
    """
    import uuid
    from datetime import UTC, datetime

    if signals.empty:
        return 0

    topic = "pyhron.strategy.signals.momentum"

    # Order: EXIT_LONG, ENTRY_LONG, HOLD
    signal_order = {"EXIT_LONG": 0, "ENTRY_LONG": 1, "HOLD": 2}
    ordered = signals.copy()
    ordered["_sort_key"] = ordered["signal_type"].map(
        lambda x: signal_order.get(x, 3),
    )
    ordered = ordered.sort_values("_sort_key")

    published = 0
    now = datetime.now(tz=UTC)

    for _, row in ordered.iterrows():
        event = MomentumSignalEvent(
            event_id=str(uuid.uuid4()),
            event_type="MOMENTUM_SIGNAL",
            strategy_id=strategy_id,
            rebalance_date=rebalance_date.isoformat(),
            symbol=str(row.get("symbol", "")),
            signal_type=str(row.get("signal_type", "ENTRY_LONG")),
            momentum_score=round(float(row.get("momentum_score", 0)), 6),
            rank=int(row.get("rank", 0)),
            universe_size=int(row.get("universe_size", 0)),
            target_weight=float(row.get("target_weight", 0)),
            target_lots=int(row.get("target_lots", 0)),
            sector=str(row.get("sector", "")),
            generated_at=now.isoformat(),
        )
        try:
            if kafka_producer._producer is None:
                raise RuntimeError("Kafka producer not initialized")
            payload = json.dumps(event.__dict__).encode("utf-8")
            await kafka_producer._producer.send_and_wait(
                topic,
                value=payload,
                key=strategy_id.encode("utf-8"),
            )
            published += 1
        except Exception as exc:
            logger.error(
                "momentum_signal_publish_failed",
                symbol=event.symbol,
                error=str(exc),
            )

    logger.info(
        "momentum_signals_published",
        total=len(ordered),
        published=published,
        rebalance_date=rebalance_date.isoformat(),
    )
    return published


@dataclass(frozen=True)
class MomentumSignalEvent:
    """Momentum signal Kafka message schema."""

    event_id: str
    event_type: str
    strategy_id: str
    rebalance_date: str
    symbol: str
    signal_type: str
    momentum_score: float
    rank: int
    universe_size: int
    target_weight: float
    target_lots: int
    sector: str
    generated_at: str
