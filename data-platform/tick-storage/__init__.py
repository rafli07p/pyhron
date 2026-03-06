"""
Tick storage engine for the Enthropy data platform.

Redis-backed tick cache with write, read, and pub/sub subscription
support.  Includes TTL management, zlib compression, AES encryption
for sensitive fields, and full multi-tenant isolation.
"""

from __future__ import annotations

import asyncio
import json
import time
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator, Callable, Optional, Sequence

import redis.asyncio as aioredis
import structlog
from cryptography.fernet import Fernet
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Tick:
    """Single market-data tick."""

    symbol: str
    price: float
    size: float
    timestamp: float  # UNIX epoch seconds (microsecond precision OK)
    exchange: str = ""
    conditions: list[str] = field(default_factory=list)
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Tick":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# TickStorageEngine
# ---------------------------------------------------------------------------

_DEFAULT_TTL = 86_400  # 24 h
_COMPRESSION_THRESHOLD = 256  # bytes – compress payloads larger than this
_PUBSUB_CHANNEL_PREFIX = "enthropy:ticks:"
_KEY_PREFIX = "enthropy:tickstore"


class TickStorageEngine:
    """Redis-backed tick storage with compression, encryption, and pub/sub.

    Parameters
    ----------
    redis_url : str
        Redis connection URL (e.g. ``redis://localhost:6379/0``).
    tenant_id : str
        Tenant identifier for key-namespace isolation.
    encryption_key : str | bytes | None
        Fernet key used to encrypt tick payloads at rest.  When ``None``
        ticks are stored compressed but unencrypted.
    default_ttl : int
        Default time-to-live in seconds for tick data in Redis.
    max_ticks_per_key : int
        Maximum number of ticks stored per symbol sorted-set before the
        oldest entries are evicted.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        tenant_id: str = "default",
        encryption_key: Optional[str | bytes] = None,
        default_ttl: int = _DEFAULT_TTL,
        max_ticks_per_key: int = 500_000,
    ) -> None:
        self.tenant_id = tenant_id
        self._redis_url = redis_url
        self._default_ttl = default_ttl
        self._max_ticks = max_ticks_per_key
        self._log = logger.bind(tenant_id=tenant_id, component="TickStorageEngine")

        # Lazy-initialised Redis pool
        self._redis: Optional[aioredis.Redis] = None

        # Optional Fernet encryption
        self._fernet: Optional[Fernet] = None
        if encryption_key:
            key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
            self._fernet = Fernet(key)

        # Track active subscriptions for graceful shutdown
        self._subscriptions: dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=False,
                max_connections=20,
            )
            self._log.info("redis_connected", url=self._redis_url)
        return self._redis

    async def close(self) -> None:
        """Cancel subscriptions and close the Redis connection."""
        for task in self._subscriptions.values():
            task.cancel()
        self._subscriptions.clear()
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            self._log.info("redis_connection_closed")

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def _key(self, symbol: str) -> str:
        return f"{_KEY_PREFIX}:{self.tenant_id}:{symbol.upper()}"

    def _channel(self, symbol: str) -> str:
        return f"{_PUBSUB_CHANNEL_PREFIX}{self.tenant_id}:{symbol.upper()}"

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def _encode(self, tick: Tick) -> bytes:
        raw = json.dumps(tick.to_dict(), separators=(",", ":")).encode()
        if len(raw) >= _COMPRESSION_THRESHOLD:
            raw = zlib.compress(raw, level=6)
        if self._fernet:
            raw = self._fernet.encrypt(raw)
        return raw

    def _decode(self, data: bytes) -> Tick:
        raw = data
        if self._fernet:
            raw = self._fernet.decrypt(raw)
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            pass  # wasn't compressed
        return Tick.from_dict(json.loads(raw))

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.2, max=2),
        retry=retry_if_exception_type((aioredis.ConnectionError, aioredis.TimeoutError, OSError)),
        reraise=True,
    )
    async def write_tick(self, tick: Tick, *, ttl: Optional[int] = None) -> None:
        """Persist a single tick to Redis and publish to subscribers.

        The tick is stored in a sorted set keyed by ``symbol`` with the
        UNIX timestamp as the score, enabling efficient range queries.
        """
        r = await self._get_redis()
        key = self._key(tick.symbol)
        encoded = self._encode(tick)

        pipe = r.pipeline(transaction=True)
        pipe.zadd(key, {encoded: tick.timestamp})
        pipe.expire(key, ttl or self._default_ttl)
        await pipe.execute()

        # Trim to max length (drop oldest)
        count = await r.zcard(key)
        if count > self._max_ticks:
            await r.zremrangebyrank(key, 0, count - self._max_ticks - 1)

        # Publish for real-time subscribers
        channel = self._channel(tick.symbol)
        await r.publish(channel, encoded)

        self._log.debug(
            "tick_written",
            symbol=tick.symbol,
            price=tick.price,
            ts=tick.timestamp,
        )

    async def write_ticks(self, ticks: Sequence[Tick], *, ttl: Optional[int] = None) -> int:
        """Batch-write multiple ticks.  Returns the count written."""
        r = await self._get_redis()
        pipe = r.pipeline(transaction=False)

        for tick in ticks:
            key = self._key(tick.symbol)
            encoded = self._encode(tick)
            pipe.zadd(key, {encoded: tick.timestamp})
            pipe.expire(key, ttl or self._default_ttl)

        results = await pipe.execute()
        self._log.info("ticks_batch_written", count=len(ticks))
        return len(ticks)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.2, max=2),
        retry=retry_if_exception_type((aioredis.ConnectionError, aioredis.TimeoutError, OSError)),
        reraise=True,
    )
    async def read_ticks(
        self,
        symbol: str,
        *,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
        limit: int = 10_000,
    ) -> list[Tick]:
        """Read ticks for *symbol* within an optional time range.

        Parameters
        ----------
        symbol : str
            Ticker symbol.
        start_ts / end_ts : float | None
            UNIX-epoch bounds (inclusive).  Defaults to ``-inf`` / ``+inf``.
        limit : int
            Maximum ticks to return (newest first by default).
        """
        r = await self._get_redis()
        key = self._key(symbol)

        min_score = start_ts if start_ts is not None else "-inf"
        max_score = end_ts if end_ts is not None else "+inf"

        raw_entries: list[bytes] = await r.zrangebyscore(
            key, min=min_score, max=max_score, start=0, num=limit,
        )

        ticks = [self._decode(entry) for entry in raw_entries]
        self._log.debug("ticks_read", symbol=symbol, count=len(ticks))
        return ticks

    async def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        """Return the most recent tick for *symbol*, or ``None``."""
        r = await self._get_redis()
        key = self._key(symbol)
        entries = await r.zrevrange(key, 0, 0)
        if not entries:
            return None
        return self._decode(entries[0])

    # ------------------------------------------------------------------
    # Subscribe (pub/sub)
    # ------------------------------------------------------------------

    async def subscribe_ticks(
        self,
        symbol: str,
        callback: Callable[[Tick], None],
    ) -> None:
        """Subscribe to real-time tick updates for *symbol*.

        Parameters
        ----------
        symbol : str
            Ticker symbol to subscribe to.
        callback : Callable[[Tick], None]
            Invoked for every tick received.  May be a coroutine function.
        """
        r = await self._get_redis()
        channel = self._channel(symbol)
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        self._log.info("subscribed", symbol=symbol, channel=channel)

        async def _listener() -> None:
            try:
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        tick = self._decode(message["data"])
                        if asyncio.iscoroutinefunction(callback):
                            await callback(tick)
                        else:
                            callback(tick)
                    except Exception:
                        self._log.exception("subscribe_callback_error", symbol=symbol)
            except asyncio.CancelledError:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
                self._log.info("unsubscribed", symbol=symbol)

        task = asyncio.create_task(_listener(), name=f"tick-sub-{symbol}")
        self._subscriptions[symbol] = task

    async def unsubscribe_ticks(self, symbol: str) -> None:
        """Cancel an active subscription for *symbol*."""
        task = self._subscriptions.pop(symbol, None)
        if task:
            task.cancel()
            self._log.info("unsubscribed", symbol=symbol)

    # ------------------------------------------------------------------
    # TTL management
    # ------------------------------------------------------------------

    async def set_ttl(self, symbol: str, ttl: int) -> bool:
        """Update TTL for a symbol's tick set.  Returns ``True`` on success."""
        r = await self._get_redis()
        key = self._key(symbol)
        result = await r.expire(key, ttl)
        self._log.info("ttl_updated", symbol=symbol, ttl=ttl, success=result)
        return bool(result)

    async def get_ttl(self, symbol: str) -> int:
        """Return remaining TTL in seconds (``-1`` if no expiry, ``-2`` if missing)."""
        r = await self._get_redis()
        return await r.ttl(self._key(symbol))

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    async def purge_symbol(self, symbol: str) -> bool:
        """Delete all ticks for *symbol*."""
        r = await self._get_redis()
        deleted = await r.delete(self._key(symbol))
        self._log.info("symbol_purged", symbol=symbol, deleted=bool(deleted))
        return bool(deleted)

    async def symbol_count(self, symbol: str) -> int:
        """Return the number of ticks stored for *symbol*."""
        r = await self._get_redis()
        return await r.zcard(self._key(symbol))


__all__ = [
    "Tick",
    "TickStorageEngine",
]
