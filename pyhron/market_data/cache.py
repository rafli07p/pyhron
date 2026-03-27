"""Redis-backed market data cache for the Pyhron trading platform.

Provides sub-millisecond access to the latest tick data per symbol.
Each tick is stored as a JSON hash with a configurable TTL.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal

from pyhron.shared.schemas.tick import TickData

logger = logging.getLogger(__name__)

_KEY_PREFIX = "pyhron:mktdata:tick:"


class MarketDataCache:
    """Async Redis cache for latest tick data.

    Parameters
    ----------
    redis_url:
        Redis connection URL (e.g. ``redis://localhost:6379/0``).
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self.redis_url = redis_url
        self._redis = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=True,
        )
        await self._redis.ping()
        logger.info("market_data_cache.connected", extra={"url": self.redis_url})

    async def disconnect(self) -> None:
        """Close the Redis connection."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            logger.info("market_data_cache.disconnected")

    async def set_latest_tick(self, tick: TickData, ttl_seconds: int = 60) -> None:
        """Cache a tick with expiration.

        Parameters
        ----------
        tick:
            The tick data to cache.
        ttl_seconds:
            Time-to-live in seconds (default 60s).
        """
        if self._redis is None:
            raise RuntimeError("Cache not connected")

        key = f"{_KEY_PREFIX}{tick.symbol}"
        payload = json.dumps(
            {
                "symbol": tick.symbol,
                "price": str(tick.price),
                "volume": tick.volume,
                "bid": str(tick.bid),
                "ask": str(tick.ask),
                "timestamp": tick.timestamp.isoformat(),
                "exchange": tick.exchange,
            }
        )
        await self._redis.set(key, payload, ex=ttl_seconds)

    async def get_latest_tick(self, symbol: str) -> TickData | None:
        """Retrieve the cached tick for a symbol.

        Returns None if the key does not exist or has expired.
        """
        if self._redis is None:
            raise RuntimeError("Cache not connected")

        key = f"{_KEY_PREFIX}{symbol}"
        raw = await self._redis.get(key)
        if raw is None:
            return None

        data = json.loads(raw)
        return TickData(
            symbol=data["symbol"],
            price=Decimal(data["price"]),
            volume=int(data["volume"]),
            bid=Decimal(data["bid"]),
            ask=Decimal(data["ask"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            exchange=data["exchange"],
        )

    async def flush_test_data(self) -> None:
        """Remove all cached tick data (for testing only)."""
        if self._redis is None:
            raise RuntimeError("Cache not connected")

        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{_KEY_PREFIX}*", count=100)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break
