"""Per-IP rate limiter middleware.

IP-based rate limiting using a Redis backend with sliding window counters.
Returns 429 Too Many Requests when the limit is exceeded.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

DEFAULT_RATE_LIMIT = 100  # requests per window
DEFAULT_WINDOW_SECONDS = 60


# ── In-Memory Fallback Store ────────────────────────────────────────────────


class _InMemoryStore:
    """Simple in-memory sliding window counter (fallback when Redis unavailable)."""

    def __init__(self) -> None:
        self._counters: dict[str, list[float]] = {}

    def is_rate_limited(self, key: str, limit: int, window: int) -> tuple[bool, int, int]:
        """Check and increment counter. Returns (limited, remaining, reset_after)."""
        now = time.monotonic()
        if key not in self._counters:
            self._counters[key] = []

        # Prune expired entries
        self._counters[key] = [ts for ts in self._counters[key] if now - ts < window]
        count = len(self._counters[key])

        if count >= limit:
            oldest = self._counters[key][0] if self._counters[key] else now
            reset_after = int(window - (now - oldest))
            return True, 0, max(reset_after, 1)

        self._counters[key].append(now)
        return False, limit - count - 1, window


# ── Redis Store ──────────────────────────────────────────────────────────────


_RATE_LIMIT_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


class _RedisStore:
    """Redis-backed sliding window rate limiter."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def is_rate_limited(self, key: str, limit: int, window: int) -> tuple[bool, int, int]:
        """Atomic increment with TTL-based expiration in Redis."""
        redis_key = f"rate_limit:{key}"
        current = await self._redis.eval(_RATE_LIMIT_LUA, 1, redis_key, window)
        ttl = await self._redis.ttl(redis_key)
        if current > limit:
            return True, 0, max(ttl, 1)
        return False, limit - current, max(ttl, 1)


# ── Middleware ───────────────────────────────────────────────────────────────


class PerIPRateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate-limit incoming requests by client IP address."""

    def __init__(
        self,
        app: Any,
        redis_client: Any | None = None,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        if redis_client is not None:
            self._store: Any = _RedisStore(redis_client)
            self._async = True
        else:
            self._store = _InMemoryStore()
            self._async = False

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For behind a proxy."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = self._get_client_ip(request)

        if self._async:
            limited, remaining, reset_after = await self._store.is_rate_limited(
                client_ip, self.rate_limit, self.window_seconds
            )
        else:
            limited, remaining, reset_after = self._store.is_rate_limited(
                client_ip, self.rate_limit, self.window_seconds
            )

        if limited:
            logger.warning("rate_limit_exceeded", client_ip=client_ip)
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(reset_after),
                    "X-RateLimit-Limit": str(self.rate_limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
