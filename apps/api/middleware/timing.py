"""Request timing middleware.

Adds X-Process-Time header and records Prometheus histogram.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from shared.logging import get_logger

logger = get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Add X-Process-Time header to every response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        return response
