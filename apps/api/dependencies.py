"""FastAPI dependency injection providers.

Shared dependencies used across routers (DB sessions, Redis, config).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shared.async_database_session import get_session
from shared.configuration_settings import Config, get_config
from shared.redis_cache_client import get_redis

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from redis.asyncio import Redis as RedisType


async def get_db() -> AsyncIterator[Any]:
    """Yield an async database session."""
    async with get_session() as session:
        yield session


async def get_cache() -> RedisType:
    """Return the shared Redis client."""
    return await get_redis()


def get_settings() -> Config:
    """Return the application config singleton."""
    return get_config()
