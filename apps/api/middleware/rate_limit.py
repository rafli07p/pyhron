"""Simple in-memory rate limiting middleware.

In production, use Redis-backed sliding window (e.g. via shared.cache).
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from shared.logging import get_logger

logger = get_logger(__name__)

# Simple in-memory token bucket per client IP
_buckets: dict[str, list[float]] = defaultdict(list)
_WINDOW_SECONDS = 60
_MAX_REQUESTS = 120


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit requests per client IP using a sliding window."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Prune expired entries
        _buckets[client_ip] = [
            ts for ts in _buckets[client_ip] if now - ts < _WINDOW_SECONDS
        ]

        if len(_buckets[client_ip]) >= _MAX_REQUESTS:
            logger.warning("rate_limit_exceeded", client_ip=client_ip)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        _buckets[client_ip].append(now)
        return await call_next(request)
