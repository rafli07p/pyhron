"""Redis pub/sub subscriber that bridges Redis channels to WebSocket clients.

Each API server instance runs one ``RedisSubscriber`` that listens to all
active Redis pub/sub channels and forwards messages to the local
``WebSocketConnectionManager``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis.asyncio as aioredis

    from services.api.websocket_gateway.connection_manager import (
        WebSocketConnectionManager,
    )

logger = logging.getLogger(__name__)


class RedisSubscriber:
    """Subscribes to Redis pub/sub channels and routes messages to
    the local ``WebSocketConnectionManager``.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        manager: WebSocketConnectionManager,
    ) -> None:
        self._redis = redis_client
        self._manager = manager
        self._pubsub: aioredis.client.PubSub | None = None  # type: ignore[name-defined]
        self._subscribed_channels: set[str] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str) -> None:
        """Subscribe to a Redis pub/sub channel."""
        async with self._lock:
            if self._pubsub is None:
                self._pubsub = self._redis.pubsub()
            if channel not in self._subscribed_channels:
                await self._pubsub.subscribe(channel)
                self._subscribed_channels.add(channel)

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a Redis pub/sub channel."""
        async with self._lock:
            if self._pubsub is not None and channel in self._subscribed_channels:
                await self._pubsub.unsubscribe(channel)
                self._subscribed_channels.discard(channel)

    async def run(self) -> None:
        """Listen for Redis pub/sub messages and forward to WebSocket clients."""
        try:
            while True:
                if self._pubsub is None:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=0.1,
                    )
                except Exception:
                    logger.exception("redis_subscriber.get_message_error")
                    await asyncio.sleep(1)
                    continue

                if message is None:
                    await asyncio.sleep(0.01)
                    continue

                if message["type"] != "message":
                    continue

                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode("utf-8")

                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                try:
                    ws_msg = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    continue

                await self._manager.broadcast_to_channel(channel, ws_msg)

        except asyncio.CancelledError:
            logger.info("redis_subscriber.cancelled")
        finally:
            if self._pubsub is not None:
                try:
                    await self._pubsub.unsubscribe()
                    await self._pubsub.aclose()
                except Exception:
                    pass
