"""Pyhron shared utilities.

Provides reusable helpers used throughout the platform:

* **retry_with_backoff** -- Decorator for retrying flaky I/O with
  exponential back-off (wraps :pypi:`tenacity`).
* **rate_limiter** -- Simple token-bucket rate limiter.
* **json_serializer** -- JSON encoder that handles ``datetime``,
  ``Decimal``, ``UUID``, and other non-standard types.
* **generate_id** -- Generate a new UUID4 string.
* **timestamp_now** -- Current UTC timestamp as an ISO-8601 string.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timezone
from decimal import Decimal
from functools import wraps
from typing import Any, TypeVar
from uuid import UUID, uuid4

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Retry with exponential back-off
# ---------------------------------------------------------------------------

def retry_with_backoff(
    max_attempts: int = 3,
    min_wait: float = 0.5,
    max_wait: float = 30.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator that retries a function with exponential back-off.

    Uses :pypi:`tenacity` under the hood.

    Args:
        max_attempts: Maximum number of attempts (including the first).
        min_wait: Minimum wait between retries in seconds.
        max_wait: Maximum wait between retries in seconds.
        retry_on: Tuple of exception types that trigger a retry.

    Returns:
        Decorated function with retry logic.

    Example::

        @retry_with_backoff(max_attempts=5, retry_on=(ConnectionError,))
        async def fetch_market_data(symbol: str) -> dict:
            ...
    """

    def decorator(func: F) -> F:
        tenacity_decorator = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_on),
            reraise=True,
        )
        wrapped: F = tenacity_decorator(func)
        return wrapped

    return decorator


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Thread-safe token-bucket rate limiter.

    Args:
        rate: Maximum number of operations per second.
        burst: Maximum burst size (defaults to ``rate``).

    Example::

        limiter = RateLimiter(rate=10, burst=20)
        if limiter.acquire():
            call_api()
        else:
            raise TooManyRequests()
    """

    def __init__(self, rate: float, burst: int | None = None) -> None:
        self._rate = rate
        self._burst = float(burst if burst is not None else int(rate))
        self._tokens = self._burst
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> bool:
        """Try to consume *tokens* from the bucket.

        Returns ``True`` if the tokens were available, ``False`` otherwise.
        """
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def wait(self, tokens: float = 1.0, timeout: float = 30.0) -> bool:
        """Block until *tokens* are available or *timeout* expires.

        Returns ``True`` if tokens were acquired, ``False`` on timeout.
        """
        deadline = time.monotonic() + timeout
        while True:
            if self.acquire(tokens):
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            # Sleep for approximately the time needed for one token
            time.sleep(min(1.0 / self._rate, remaining))

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens (approximate)."""
        with self._lock:
            self._refill()
            return self._tokens


def rate_limiter(rate: float, burst: int | None = None) -> RateLimiter:
    """Factory function to create a :class:`RateLimiter`.

    Args:
        rate: Maximum operations per second.
        burst: Maximum burst size.

    Returns:
        A new ``RateLimiter`` instance.
    """
    return RateLimiter(rate=rate, burst=burst)


# ---------------------------------------------------------------------------
# JSON serializer
# ---------------------------------------------------------------------------

class PyhronJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles financial-domain types.

    Supported types beyond the standard library:

    * ``datetime`` / ``date`` -- ISO-8601 string
    * ``Decimal`` -- string to preserve precision
    * ``UUID`` -- string representation
    * ``set`` / ``frozenset`` -- converted to sorted list
    * ``bytes`` -- UTF-8 decoded string
    * Objects with a ``model_dump()`` method (Pydantic v2)
    * Objects with a ``dict()`` method (Pydantic v1 fallback)
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (set, frozenset)):
            return sorted(obj)
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if hasattr(obj, "dict"):
            return obj.dict()
        return super().default(obj)


def json_serializer(obj: Any, *, indent: int | None = None, sort_keys: bool = False) -> str:
    """Serialize *obj* to a JSON string using :class:`PyhronJSONEncoder`.

    Handles ``datetime``, ``Decimal``, ``UUID``, Pydantic models, and
    other types commonly used in trading applications.

    Args:
        obj: Object to serialize.
        indent: JSON indentation level (``None`` for compact).
        sort_keys: Whether to sort dictionary keys.

    Returns:
        JSON string.
    """
    return json.dumps(obj, cls=PyhronJSONEncoder, indent=indent, sort_keys=sort_keys)


def json_deserialize(raw: str | bytes) -> Any:
    """Deserialize a JSON string.

    A thin wrapper around ``json.loads`` included for symmetry with
    :func:`json_serializer`.
    """
    return json.loads(raw)


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def generate_id() -> str:
    """Generate a new UUID4 string.

    Returns:
        Lowercase hex UUID string (e.g. ``'a1b2c3d4-...'``).
    """
    return str(uuid4())


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------

def timestamp_now() -> datetime:
    """Return the current UTC time as a timezone-aware ``datetime``.

    Returns:
        ``datetime`` object with ``tzinfo=timezone.utc``.
    """
    return datetime.now(tz=UTC)


def timestamp_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        ISO-8601 formatted string (e.g. ``'2024-01-15T10:30:00+00:00'``).
    """
    return timestamp_now().isoformat()


__all__ = [
    "PyhronJSONEncoder",
    "RateLimiter",
    "generate_id",
    "json_deserialize",
    "json_serializer",
    "rate_limiter",
    "retry_with_backoff",
    "timestamp_now",
    "timestamp_now_iso",
]
