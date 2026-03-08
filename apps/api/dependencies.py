"""FastAPI dependency injection providers.

Shared dependencies used across routers (DB sessions, Redis, config).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from shared.cache import get_redis
from shared.config import Config, get_config
from shared.database import get_session


async def get_db() -> AsyncIterator:
    """Yield an async database session."""
    async with get_session() as session:
        yield session


async def get_cache():
    """Return the shared Redis client."""
    return await get_redis()


def get_settings() -> Config:
    """Return the application config singleton."""
    return get_config()
