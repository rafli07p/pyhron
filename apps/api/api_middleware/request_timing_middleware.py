"""Request timing middleware.

Measures request duration and logs it via structured logging.
Optionally records a Prometheus histogram for observability.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from fastapi import Request, Response

logger = get_logger(__name__)

# ── Prometheus Histogram (lazy init) ────────────────────────────────────────

_histogram: Any = None


def _get_histogram() -> Any:
    """Lazily create the Prometheus histogram to avoid import errors."""
    global _histogram
    if _histogram is None:
        try:
            from prometheus_client import Histogram

            _histogram = Histogram(
                "http_request_duration_seconds",
                "HTTP request duration in seconds",
                labelnames=["method", "path", "status_code"],
                buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            )
        except ImportError:
            _histogram = False  # sentinel: prometheus_client not installed
    return _histogram if _histogram is not False else None


# ── Path Normalization ───────────────────────────────────────────────────────


def _normalize_path(path: str) -> str:
    """Normalize path for Prometheus labels to avoid cardinality explosion.

    Replaces dynamic path segments (UUIDs, numeric IDs) with placeholders.
    """
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        # Replace UUIDs and numeric IDs with placeholder
        if (len(part) == 36 and part.count("-") == 4) or part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized)


# ── Middleware ───────────────────────────────────────────────────────────────


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Measure and log HTTP request duration. Optionally export to Prometheus."""

    def __init__(self, app: Any, slow_request_threshold: float = 1.0) -> None:
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start_time
        status_code = response.status_code
        method = request.method
        path = request.url.path

        # Add timing header
        response.headers["X-Request-Duration-Ms"] = f"{duration * 1000:.2f}"

        # Structured log
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2),
        }

        if duration >= self.slow_request_threshold:
            logger.warning("slow_request", **log_data)
        else:
            logger.info("request_completed", **log_data)

        # Prometheus histogram
        histogram = _get_histogram()
        if histogram is not None:
            normalized = _normalize_path(path)
            histogram.labels(
                method=method,
                path=normalized,
                status_code=str(status_code),
            ).observe(duration)

        return response
