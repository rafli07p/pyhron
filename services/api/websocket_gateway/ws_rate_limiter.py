"""Per-connection WebSocket rate limiter backed by Redis sliding window.

Uses a sorted-set-based sliding window executed atomically via a Lua
script for correctness under concurrency.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Lua script: ZADD current timestamp, ZREMRANGEBYSCORE to trim window,
# ZCARD to count, EXPIRE to auto-cleanup.  Returns current count.
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
redis.call('ZADD', key, now, now .. ':' .. math.random(1, 1000000))
local count = redis.call('ZCARD', key)
redis.call('EXPIRE', key, window + 10)
return count
"""


class WebSocketRateLimiter:
    """Per-connection rate limiter using a Redis sliding window.

    Limits
    ------
    - Inbound messages: 100 per minute per connection
    - Subscribe requests: 20 per minute per connection
    """

    INBOUND_LIMIT = 100
    SUBSCRIBE_LIMIT = 20
    WINDOW_SECONDS = 60

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis: aioredis.Redis = redis_client
        self._script: object | None = None

    async def _ensure_script(self) -> object:
        if self._script is None:
            self._script = self._redis.register_script(_SLIDING_WINDOW_LUA)
        return self._script

    async def _check(self, key: str, limit: int) -> bool:
        script = await self._ensure_script()
        now_ms = int(time.time() * 1000)
        window_ms = self.WINDOW_SECONDS * 1000
        count: int = await script(keys=[key], args=[now_ms, window_ms])  # type: ignore[operator]
        return int(count) <= limit

    async def check_inbound(self, connection_id: str) -> bool:
        """Returns ``True`` if the inbound message is allowed."""
        key = f"pyhron:ratelimit:ws:inbound:{connection_id}"
        return await self._check(key, self.INBOUND_LIMIT)

    async def check_subscribe(self, connection_id: str) -> bool:
        """Returns ``True`` if the subscribe request is allowed."""
        key = f"pyhron:ratelimit:ws:subscribe:{connection_id}"
        return await self._check(key, self.SUBSCRIBE_LIMIT)

    async def cleanup(self, connection_id: str) -> None:
        """Remove rate-limit keys when a connection closes."""
        pipe = self._redis.pipeline()
        pipe.delete(f"pyhron:ratelimit:ws:inbound:{connection_id}")
        pipe.delete(f"pyhron:ratelimit:ws:subscribe:{connection_id}")
        await pipe.execute()
