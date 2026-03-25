"""Pyhron API entrypoint.

Provides the ASGI ``app`` instance used by uvicorn::

    uvicorn services.api.main:app --host 0.0.0.0 --port 8000

Starts the REST gateway, WebSocket endpoint, Kafka-Redis bridges,
and market status broadcaster as background tasks.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import redis.asyncio as aioredis

from services.api.rest_gateway import create_rest_app

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
from services.api.websocket_gateway.connection_manager import (
    WebSocketConnectionManager,
)
from services.api.websocket_gateway.kafka_redis_bridge import (
    KafkaRedisBridge,
    MessageRouter,
)
from services.api.websocket_gateway.market_status_broadcaster import (
    MarketStatusBroadcaster,
)
from services.api.websocket_gateway.redis_subscriber import RedisSubscriber
from services.api.websocket_gateway.ws_endpoint import router as ws_router
from services.api.websocket_gateway.ws_rate_limiter import WebSocketRateLimiter
from shared.configuration_settings import get_config
from shared.kafka_topics import KafkaTopic

logger = logging.getLogger(__name__)

_TOPICS_TO_BRIDGE = [
    KafkaTopic.VALIDATED_EOD_OHLCV,
    KafkaTopic.RAW_INTRADAY_TRADES,
    KafkaTopic.RAW_INTRADAY_BARS,
    KafkaTopic.ORDER_SUBMITTED,
    KafkaTopic.ORDER_FILLED,
    KafkaTopic.POSITION_UPDATED,
    KafkaTopic.MOMENTUM_SIGNALS,
    KafkaTopic.ML_SIGNALS,
    KafkaTopic.PAPER_NAV_SNAPSHOT,
    KafkaTopic.PAPER_REBALANCE_RESULT,
]


def _create_kafka_consumer(topic: str):  # type: ignore[no-untyped-def]
    """Create an AIOKafkaConsumer for the given topic."""
    from aiokafka import AIOKafkaConsumer

    config = get_config()
    return AIOKafkaConsumer(
        topic,
        bootstrap_servers=config.kafka_bootstrap_servers,
        group_id=f"pyhron-ws-bridge-{topic}",
        auto_offset_reset="latest",
        enable_auto_commit=True,
        value_deserializer=lambda v: v,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage WebSocket infrastructure lifecycle."""
    config = get_config()
    redis_client: aioredis.Redis = aioredis.from_url(  # type: ignore[no-untyped-call]
        config.redis_url,
        decode_responses=True,
        max_connections=50,
    )

    manager = WebSocketConnectionManager(redis_client)
    rate_limiter = WebSocketRateLimiter(redis_client)
    redis_subscriber = RedisSubscriber(redis_client, manager)

    app.state.ws_manager = manager
    app.state.ws_rate_limiter = rate_limiter

    background_tasks: list[asyncio.Task[None]] = []

    # Kafka → Redis bridges
    router = MessageRouter()
    for topic in _TOPICS_TO_BRIDGE:
        try:
            consumer = _create_kafka_consumer(topic)
            bridge = KafkaRedisBridge(
                topic=topic,
                kafka_consumer=consumer,
                redis_client=redis_client,
                router=router,
            )
            task: asyncio.Task[None] = asyncio.create_task(bridge.run(), name=f"bridge:{topic}")
            background_tasks.append(task)
        except Exception:
            logger.warning("bridge.skip topic=%s (Kafka unavailable)", topic)

    # Redis pub/sub → WebSocket subscriber
    sub_task: asyncio.Task[None] = asyncio.create_task(redis_subscriber.run(), name="redis_subscriber")
    background_tasks.append(sub_task)

    # Market status broadcaster
    broadcaster = MarketStatusBroadcaster()
    status_task: asyncio.Task[None] = asyncio.create_task(broadcaster.run(manager), name="market_status_broadcaster")
    background_tasks.append(status_task)

    logger.info("ws.lifespan.started bridges=%d", len(background_tasks))

    yield

    # Shutdown
    for task in background_tasks:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    await redis_client.aclose()
    logger.info("ws.lifespan.stopped")


def create_app() -> FastAPI:
    """Build the combined REST + WebSocket FastAPI application."""
    app = create_rest_app()

    # Replace default lifespan with our custom one
    app.router.lifespan_context = lifespan

    # Mount WebSocket router
    app.include_router(ws_router)

    return app


app = create_app()
