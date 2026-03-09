"""Unit tests for OHLCV data quality validation.

Validates:
  - high >= open and high >= close
  - low <= open and low <= close
  - volume >= 0
  - No zero prices (open, high, low, close must be > 0)
  - Timestamps must be in chronological order
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


# ── Validator (pure functions under test) ───────────────────────────────────


def validate_ohlcv_bar(bar: dict) -> list[str]:
    """Validate a single OHLCV bar. Returns list of error messages (empty = valid)."""
    errors = []
    o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
    v = bar["volume"]

    # No zero or negative prices
    for field in ("open", "high", "low", "close"):
        if bar[field] <= 0:
            errors.append(f"{field} must be > 0, got {bar[field]}")

    # High/low bounds
    if h < o:
        errors.append(f"high ({h}) < open ({o})")
    if h < c:
        errors.append(f"high ({h}) < close ({c})")
    if l > o:
        errors.append(f"low ({l}) > open ({o})")
    if l > c:
        errors.append(f"low ({l}) > close ({c})")

    # Volume non-negative
    if v < 0:
        errors.append(f"volume must be >= 0, got {v}")

    return errors


def validate_timestamp_order(bars: list[dict]) -> list[str]:
    """Validate that timestamps are in strictly ascending order."""
    errors = []
    for i in range(1, len(bars)):
        if bars[i]["time"] <= bars[i - 1]["time"]:
            errors.append(
                f"Timestamp at index {i} ({bars[i]['time']}) is not after "
                f"index {i-1} ({bars[i-1]['time']})"
            )
    return errors


# ── Valid Bar Tests ─────────────────────────────────────────────────────────


class TestValidBars:
    def test_normal_bar_passes(self):
        bar = {"open": 9200, "high": 9350, "low": 9150, "close": 9300, "volume": 12_500_000}
        assert validate_ohlcv_bar(bar) == []

    def test_doji_bar_passes(self):
        """Open == close == high == low is valid."""
        bar = {"open": 9200, "high": 9200, "low": 9200, "close": 9200, "volume": 1000}
        assert validate_ohlcv_bar(bar) == []

    def test_zero_volume_is_valid(self):
        bar = {"open": 9200, "high": 9300, "low": 9100, "close": 9250, "volume": 0}
        assert validate_ohlcv_bar(bar) == []


# ── Invalid Bar Tests ──────────────────────────────────────────────────────


class TestInvalidBars:
    def test_high_below_open(self):
        bar = {"open": 9200, "high": 9100, "low": 9050, "close": 9080, "volume": 1000}
        errors = validate_ohlcv_bar(bar)
        assert any("high" in e and "open" in e for e in errors)

    def test_high_below_close(self):
        bar = {"open": 9000, "high": 9100, "low": 8900, "close": 9200, "volume": 1000}
        errors = validate_ohlcv_bar(bar)
        assert any("high" in e and "close" in e for e in errors)

    def test_low_above_open(self):
        bar = {"open": 9000, "high": 9300, "low": 9100, "close": 9200, "volume": 1000}
        errors = validate_ohlcv_bar(bar)
        assert any("low" in e and "open" in e for e in errors)

    def test_low_above_close(self):
        bar = {"open": 9200, "high": 9300, "low": 9150, "close": 9100, "volume": 1000}
        errors = validate_ohlcv_bar(bar)
        assert any("low" in e and "close" in e for e in errors)

    def test_negative_volume(self):
        bar = {"open": 9200, "high": 9300, "low": 9100, "close": 9250, "volume": -500}
        errors = validate_ohlcv_bar(bar)
        assert any("volume" in e for e in errors)

    def test_zero_open_price(self):
        bar = {"open": 0, "high": 9300, "low": 9100, "close": 9250, "volume": 1000}
        errors = validate_ohlcv_bar(bar)
        assert any("open" in e for e in errors)

    def test_zero_close_price(self):
        bar = {"open": 9200, "high": 9300, "low": 9100, "close": 0, "volume": 1000}
        errors = validate_ohlcv_bar(bar)
        assert any("close" in e for e in errors)

    def test_multiple_errors_returned(self):
        bar = {"open": 0, "high": 0, "low": 0, "close": 0, "volume": -1}
        errors = validate_ohlcv_bar(bar)
        assert len(errors) >= 5  # 4 zero prices + negative volume


# ── Timestamp Order Tests ──────────────────────────────────────────────────


class TestTimestampOrder:
    def test_ordered_timestamps_pass(self):
        bars = [
            {"time": datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)},
            {"time": datetime(2025, 1, 7, 9, 0, tzinfo=timezone.utc)},
            {"time": datetime(2025, 1, 8, 9, 0, tzinfo=timezone.utc)},
        ]
        assert validate_timestamp_order(bars) == []

    def test_duplicate_timestamps_fail(self):
        bars = [
            {"time": datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)},
            {"time": datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)},
        ]
        errors = validate_timestamp_order(bars)
        assert len(errors) == 1

    def test_reversed_timestamps_fail(self):
        bars = [
            {"time": datetime(2025, 1, 7, 9, 0, tzinfo=timezone.utc)},
            {"time": datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)},
        ]
        errors = validate_timestamp_order(bars)
        assert len(errors) == 1

    def test_single_bar_passes(self):
        bars = [{"time": datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)}]
        assert validate_timestamp_order(bars) == []
