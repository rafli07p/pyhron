"""Kafka → Redis pub/sub bridge for WebSocket fan-out.

Layer 1 of the two-layer architecture: one Kafka consumer per topic
reads events and publishes to Redis pub/sub channels, decoupling the
ingestion pipeline from the number of connected WebSocket clients.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shared.kafka_topics import KafkaTopic

if TYPE_CHECKING:
    import redis.asyncio as aioredis
    from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class MessageRouter:
    """Determines the target Redis channel for a Kafka message."""

    _TOPIC_MAP: dict[str, str] = {
        KafkaTopic.VALIDATED_EOD_OHLCV: "quotes",
        KafkaTopic.ORDER_SUBMITTED: "orders",
        KafkaTopic.ORDER_FILLED: "orders",
        KafkaTopic.POSITION_UPDATED: "positions",
        KafkaTopic.MOMENTUM_SIGNALS: "signals",
        KafkaTopic.ML_SIGNALS: "signals",
        KafkaTopic.PAPER_NAV_SNAPSHOT: "paper_nav",
        KafkaTopic.PAPER_REBALANCE_RESULT: "paper_rebalance",
    }

    def route(self, topic: str, payload: dict) -> str | None:  # type: ignore[type-arg]
        """Return Redis channel string, or ``None`` to drop the message."""
        channel_type = self._TOPIC_MAP.get(topic)
        if channel_type is None:
            return None

        if channel_type == "quotes":
            symbol = payload.get("symbol")
            return f"pyhron:quotes:{symbol}" if symbol else None

        if channel_type == "orders":
            user_id = payload.get("user_id")
            return f"pyhron:orders:{user_id}" if user_id else None

        if channel_type == "positions":
            user_id = payload.get("user_id")
            return f"pyhron:positions:{user_id}" if user_id else None

        if channel_type == "signals":
            strategy_id = payload.get("strategy_id")
            return f"pyhron:signals:{strategy_id}" if strategy_id else None

        if channel_type == "paper_nav":
            session_id = payload.get("session_id")
            return f"pyhron:paper:nav:{session_id}" if session_id else None

        if channel_type == "paper_rebalance":
            session_id = payload.get("session_id")
            return f"pyhron:paper:rebalance:{session_id}" if session_id else None

        return None


def _transform_eod_to_quote(payload: dict) -> dict:  # type: ignore[type-arg]
    """Transform a validated EOD OHLCV record to a ``QUOTE_UPDATE``."""
    now_iso = datetime.now(UTC).isoformat()
    return {
        "type": "QUOTE_UPDATE",
        "symbol": str(payload.get("symbol", "")),
        "timestamp": str(payload.get("date", now_iso)),
        "open": str(payload.get("open", "")),
        "high": str(payload.get("high", "")),
        "low": str(payload.get("low", "")),
        "close": str(payload.get("close", "")),
        "volume": str(payload.get("volume", "")),
        "value_idr": str(payload.get("value_idr", "")),
        "change": str(payload.get("change", "")),
        "change_pct": str(payload.get("change_pct", "")),
        "prev_close": str(payload.get("prev_close", "")),
        "bid": str(payload.get("bid", "")),
        "ask": str(payload.get("ask", "")),
        "bid_volume": str(payload.get("bid_volume", "")),
        "ask_volume": str(payload.get("ask_volume", "")),
    }


def _transform_order(payload: dict) -> dict:  # type: ignore[type-arg]
    """Transform order events to ``ORDER_UPDATE``."""
    return {
        "type": "ORDER_UPDATE",
        "order_id": str(payload.get("order_id", "")),
        "client_order_id": str(payload.get("client_order_id", "")),
        "symbol": str(payload.get("symbol", "")),
        "side": str(payload.get("side", "")),
        "order_type": str(payload.get("order_type", "")),
        "status": str(payload.get("status", "")),
        "quantity_lots": payload.get("quantity_lots", 0),
        "filled_quantity_lots": payload.get("filled_quantity_lots", 0),
        "limit_price": str(payload.get("limit_price", "")),
        "avg_fill_price": str(payload.get("avg_fill_price", "")),
        "commission_idr": str(payload.get("commission_idr", "")),
        "submitted_at": str(payload.get("submitted_at", "")),
        "filled_at": str(payload.get("filled_at", "")),
        "updated_at": str(payload.get("updated_at", "")),
    }


def _transform_position(payload: dict) -> dict:  # type: ignore[type-arg]
    """Transform position events to ``POSITION_UPDATE``."""
    return {
        "type": "POSITION_UPDATE",
        "symbol": str(payload.get("symbol", "")),
        "quantity_lots": payload.get("quantity_lots", 0),
        "avg_cost_idr": str(payload.get("avg_cost_idr", "")),
        "last_price": str(payload.get("last_price", "")),
        "unrealized_pnl_idr": str(payload.get("unrealized_pnl_idr", "")),
        "unrealized_pnl_pct": str(payload.get("unrealized_pnl_pct", "")),
        "realized_pnl_idr": str(payload.get("realized_pnl_idr", "")),
        "updated_at": str(payload.get("updated_at", "")),
    }


def _transform_signal(payload: dict) -> dict:  # type: ignore[type-arg]
    """Transform signal events to ``SIGNAL_UPDATE``."""
    return {
        "type": "SIGNAL_UPDATE",
        "strategy_id": str(payload.get("strategy_id", "")),
        "symbol": str(payload.get("symbol", "")),
        "signal_type": str(payload.get("signal_type", "")),
        "alpha_score": str(payload.get("alpha_score", "")),
        "target_weight": str(payload.get("target_weight", "")),
        "target_lots": payload.get("target_lots", 0),
        "rank": payload.get("rank", 0),
        "universe_size": payload.get("universe_size", 0),
        "generated_at": str(payload.get("generated_at", "")),
    }


def _transform_paper_nav(payload: dict) -> dict:  # type: ignore[type-arg]
    """Pass through paper NAV snapshot as PAPER_NAV_UPDATE."""
    return {
        "type": "PAPER_NAV_UPDATE",
        "session_id": str(payload.get("session_id", "")),
        "timestamp": str(payload.get("timestamp", "")),
        "nav_idr": str(payload.get("nav_idr", "")),
        "cash_idr": str(payload.get("cash_idr", "")),
        "gross_exposure_idr": str(payload.get("gross_exposure_idr", "")),
        "drawdown_pct": str(payload.get("drawdown_pct", "")),
        "daily_pnl_idr": str(payload.get("daily_pnl_idr", "")),
    }


def _transform_paper_rebalance(payload: dict) -> dict:  # type: ignore[type-arg]
    """Pass through paper rebalance result."""
    return {
        "type": "PAPER_REBALANCE_UPDATE",
        "session_id": str(payload.get("session_id", "")),
        "rebalance_at": str(payload.get("rebalance_at", "")),
        "signals_consumed": payload.get("signals_consumed", 0),
        "orders_submitted": payload.get("orders_submitted", 0),
        "orders_rejected": payload.get("orders_rejected", 0),
        "estimated_turnover_idr": str(payload.get("estimated_turnover_idr", "")),
    }


_TRANSFORMERS: dict[str, object] = {
    KafkaTopic.VALIDATED_EOD_OHLCV: _transform_eod_to_quote,
    KafkaTopic.ORDER_SUBMITTED: _transform_order,
    KafkaTopic.ORDER_FILLED: _transform_order,
    KafkaTopic.POSITION_UPDATED: _transform_position,
    KafkaTopic.MOMENTUM_SIGNALS: _transform_signal,
    KafkaTopic.ML_SIGNALS: _transform_signal,
    KafkaTopic.PAPER_NAV_SNAPSHOT: _transform_paper_nav,
    KafkaTopic.PAPER_REBALANCE_RESULT: _transform_paper_rebalance,
}


class KafkaRedisBridge:
    """Consumes from one Kafka topic and publishes to Redis pub/sub.

    Channel routing
    ---------------
    ``pyhron.validated.eod_ohlcv``        → ``pyhron:quotes:{symbol}``
    ``pyhron.orders.order_submitted``      → ``pyhron:orders:{user_id}``
    ``pyhron.orders.order_filled``         → ``pyhron:orders:{user_id}``
    ``pyhron.portfolio.position_updated``  → ``pyhron:positions:{user_id}``
    ``pyhron.strategy.signals.momentum``   → ``pyhron:signals:{strategy_id}``
    ``pyhron.strategy.signals.ml``         → ``pyhron:signals:{strategy_id}``
    """

    def __init__(
        self,
        topic: str,
        kafka_consumer: AIOKafkaConsumer,
        redis_client: aioredis.Redis,
        router: MessageRouter,
    ) -> None:
        self._topic = topic
        self._consumer = kafka_consumer
        self._redis = redis_client
        self._router = router

    async def run(self) -> None:
        """Consume Kafka messages and publish to Redis channels."""
        try:
            await self._consumer.start()
            logger.info("bridge.started topic=%s", self._topic)
            async for msg in self._consumer:
                try:
                    payload = json.loads(msg.value) if isinstance(msg.value, bytes | str) else msg.value
                    channel, ws_msg = await self._transform_message(self._topic, payload)
                    if channel is None:
                        continue
                    await self._redis.publish(channel, json.dumps(ws_msg))
                except Exception:
                    logger.exception("bridge.transform_error topic=%s", self._topic)
        except asyncio.CancelledError:
            logger.info("bridge.cancelled topic=%s", self._topic)
        finally:
            with contextlib.suppress(Exception):
                await self._consumer.stop()

    async def _transform_message(
        self,
        topic: str,
        payload: dict,  # type: ignore[type-arg]
    ) -> tuple[str | None, dict]:  # type: ignore[type-arg]
        """Return ``(redis_channel, ws_message)`` tuple."""
        channel = self._router.route(topic, payload)
        if channel is None:
            return None, {}

        transformer = _TRANSFORMERS.get(topic)
        if transformer is None:
            return None, {}

        ws_msg: dict[str, object] = transformer(payload)  # type: ignore[operator]
        return channel, ws_msg
