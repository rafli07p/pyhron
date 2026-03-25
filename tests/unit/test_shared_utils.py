"""Unit tests for shared.utils — PyhronJSONEncoder, RateLimiter, helpers."""

from __future__ import annotations

import json
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from shared.utils import (
    PyhronJSONEncoder,
    RateLimiter,
    generate_id,
    json_deserialize,
    json_serializer,
    rate_limiter,
    retry_with_backoff,
    timestamp_now,
    timestamp_now_iso,
)

# =============================================================================
# PyhronJSONEncoder
# =============================================================================


class TestPyhronJSONEncoder:
    def test_datetime_serialization(self) -> None:
        dt = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
        result = json.dumps({"ts": dt}, cls=PyhronJSONEncoder)
        assert "2024-06-15T10:30:00" in result

    def test_date_serialization(self) -> None:
        d = date(2024, 6, 15)
        result = json.dumps({"d": d}, cls=PyhronJSONEncoder)
        assert "2024-06-15" in result

    def test_decimal_serialization(self) -> None:
        result = json.dumps({"price": Decimal("1234.5678")}, cls=PyhronJSONEncoder)
        parsed = json.loads(result)
        assert parsed["price"] == "1234.5678"

    def test_uuid_serialization(self) -> None:
        uid = uuid4()
        result = json.dumps({"id": uid}, cls=PyhronJSONEncoder)
        parsed = json.loads(result)
        assert parsed["id"] == str(uid)

    def test_set_serialization(self) -> None:
        result = json.dumps({"tags": {"c", "a", "b"}}, cls=PyhronJSONEncoder)
        parsed = json.loads(result)
        assert parsed["tags"] == ["a", "b", "c"]

    def test_frozenset_serialization(self) -> None:
        result = json.dumps({"tags": frozenset({"x", "y"})}, cls=PyhronJSONEncoder)
        parsed = json.loads(result)
        assert parsed["tags"] == ["x", "y"]

    def test_bytes_serialization(self) -> None:
        result = json.dumps({"data": b"hello"}, cls=PyhronJSONEncoder)
        parsed = json.loads(result)
        assert parsed["data"] == "hello"

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError):
            json.dumps({"obj": object()}, cls=PyhronJSONEncoder)

    def test_pydantic_model_dump(self) -> None:
        class FakeModel:
            def model_dump(self, mode: str = "python") -> dict:
                return {"a": 1}

        result = json.dumps({"m": FakeModel()}, cls=PyhronJSONEncoder)
        parsed = json.loads(result)
        assert parsed["m"] == {"a": 1}


# =============================================================================
# json_serializer / json_deserialize
# =============================================================================


def test_json_serializer_roundtrip() -> None:
    data = {"price": Decimal("100.50"), "date": date(2024, 1, 1)}
    raw = json_serializer(data)
    parsed = json_deserialize(raw)
    assert parsed["price"] == "100.50"
    assert parsed["date"] == "2024-01-01"


def test_json_serializer_indent() -> None:
    raw = json_serializer({"a": 1}, indent=2)
    assert "\n" in raw


# =============================================================================
# RateLimiter
# =============================================================================


class TestRateLimiter:
    def test_acquire_within_burst(self) -> None:
        limiter = RateLimiter(rate=10, burst=5)
        # Should be able to acquire up to burst
        for _ in range(5):
            assert limiter.acquire() is True
        # Sixth should fail (no time to refill)
        assert limiter.acquire() is False

    def test_acquire_refills_over_time(self) -> None:
        limiter = RateLimiter(rate=100, burst=1)
        assert limiter.acquire() is True
        assert limiter.acquire() is False
        time.sleep(0.02)  # Wait for refill at 100/s
        assert limiter.acquire() is True

    def test_available_tokens(self) -> None:
        limiter = RateLimiter(rate=10, burst=10)
        assert limiter.available_tokens == pytest.approx(10.0, abs=0.5)
        limiter.acquire(5)
        assert limiter.available_tokens == pytest.approx(5.0, abs=0.5)

    def test_default_burst_equals_rate(self) -> None:
        limiter = RateLimiter(rate=20)
        assert limiter._burst == 20.0

    def test_wait_returns_true(self) -> None:
        limiter = RateLimiter(rate=100, burst=1)
        assert limiter.wait(timeout=1.0) is True

    def test_wait_timeout(self) -> None:
        limiter = RateLimiter(rate=0.1, burst=1)
        limiter.acquire()  # Drain
        assert limiter.wait(timeout=0.05) is False


def test_rate_limiter_factory() -> None:
    limiter = rate_limiter(10, burst=5)
    assert isinstance(limiter, RateLimiter)


# =============================================================================
# retry_with_backoff
# =============================================================================


def test_retry_with_backoff_succeeds_on_retry() -> None:
    call_count = 0

    @retry_with_backoff(max_attempts=3, min_wait=0.01, max_wait=0.02, retry_on=(ValueError,))
    def flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("not yet")
        return "ok"

    assert flaky() == "ok"
    assert call_count == 3


def test_retry_with_backoff_raises_after_max() -> None:
    @retry_with_backoff(max_attempts=2, min_wait=0.01, max_wait=0.02, retry_on=(ValueError,))
    def always_fail() -> None:
        raise ValueError("fail")

    with pytest.raises(ValueError, match="fail"):
        always_fail()


# =============================================================================
# ID / Timestamp helpers
# =============================================================================


def test_generate_id_is_valid_uuid() -> None:
    uid = generate_id()
    UUID(uid)  # Raises if invalid


def test_timestamp_now_is_utc() -> None:
    ts = timestamp_now()
    assert ts.tzinfo is not None
    assert ts.tzinfo == UTC


def test_timestamp_now_iso_format() -> None:
    iso = timestamp_now_iso()
    datetime.fromisoformat(iso)  # Raises if invalid
