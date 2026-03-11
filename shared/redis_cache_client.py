"""Redis client wrapper.

Usage::

    from shared.redis_cache_client import get_redis

    redis = await get_redis()
    await redis.set("key", "value", ex=60)
"""

from __future__ import annotations

import asyncio

from redis.asyncio import Redis

from shared.configuration_settings import get_config
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

_redis_client: Redis | None = None
_redis_lock = asyncio.Lock()


async def get_redis() -> Redis:
    """Return a shared async Redis client."""
    global _redis_client
    async with _redis_lock:
        if _redis_client is None:
            config = get_config()
            _redis_client = Redis.from_url(
                config.redis_url,
                decode_responses=True,
                max_connections=50,
                socket_timeout=5.0,
            )
            logger.info("redis_connected", url=config.redis_url.split("@")[-1])
    return _redis_client


async def close_redis() -> None:
    """Close the shared Redis client."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_disconnected")
