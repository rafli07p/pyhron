"""Tests for point-in-time data access layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from data_platform.pit_query import (
    PointInTimeQueryMixin,
    PointInTimeSession,
    PyhronLookAheadError,
    lookforward_leak_detector,
    pit_latest_ohlcv,
)


class TestValidateAsOf:
    """Test as_of validation logic."""

    def test_future_as_of_raises(self) -> None:
        future = datetime.now(tz=UTC) + timedelta(hours=1)
        session = MagicMock()
        with pytest.raises(PyhronLookAheadError, match="in the future"):
            PointInTimeSession(session, as_of=future).__enter__()

    def test_past_as_of_ok(self) -> None:
        past = datetime(2024, 1, 1, tzinfo=UTC)
        session = MagicMock()
        session.info = {}
        pit = PointInTimeSession(session, as_of=past)
        s = pit.__enter__()
        assert s.info["pit_as_of"] == past
        pit.__exit__(None, None, None)

    def test_naive_future_as_of_raises(self) -> None:
        future = datetime.now(tz=UTC).replace(tzinfo=None) + timedelta(hours=1)
        session = MagicMock()
        with pytest.raises(PyhronLookAheadError):
            PointInTimeSession(session, as_of=future).__enter__()


class TestPointInTimeSession:
    """Test PointInTimeSession context manager."""

    def test_context_manager_sets_and_clears_as_of(self) -> None:
        past = datetime(2024, 1, 1, tzinfo=UTC)
        session = MagicMock()
        session.info = {}

        pit = PointInTimeSession(session, as_of=past)
        with pit as s:
            assert s.info.get("pit_as_of") == past
        # After exit, pit_as_of should be removed
        assert "pit_as_of" not in session.info

    def test_context_manager_resets_on_exception(self) -> None:
        past = datetime(2024, 6, 15, tzinfo=UTC)
        session = MagicMock()
        session.info = {}

        pit = PointInTimeSession(session, as_of=past)
        with pytest.raises(ValueError, match="test error"), pit as s:
            assert s.info.get("pit_as_of") == past
            raise ValueError("test error")
        assert "pit_as_of" not in session.info


class TestPointInTimeQueryMixin:
    """Test PointInTimeQueryMixin filtering."""

    def test_filter_ohlcv_as_of_applies_where(self) -> None:
        query = MagicMock()
        col = MagicMock()
        col.__le__ = MagicMock(return_value="filter_expr")
        as_of = datetime(2024, 1, 1, tzinfo=UTC)

        PointInTimeQueryMixin.filter_ohlcv_as_of(query, col, as_of)
        query.where.assert_called_once()

    def test_filter_ohlcv_future_raises(self) -> None:
        query = MagicMock()
        col = MagicMock()
        future = datetime.now(tz=UTC) + timedelta(hours=1)

        with pytest.raises(PyhronLookAheadError):
            PointInTimeQueryMixin.filter_ohlcv_as_of(query, col, future)

    def test_filter_fundamental_uses_loaded_at(self) -> None:
        query = MagicMock()
        loaded_at_col = MagicMock()
        loaded_at_col.__le__ = MagicMock(return_value="filter_expr")
        as_of = datetime(2024, 1, 1, tzinfo=UTC)

        PointInTimeQueryMixin.filter_fundamental_as_of(query, loaded_at_col, as_of)
        query.where.assert_called_once()


class TestPitLatestOhlcv:
    """Test pit_latest_ohlcv helper."""

    def test_returns_none_when_no_data(self) -> None:
        session = MagicMock()
        result_mock = MagicMock()
        result_mock.fetchone.return_value = None
        session.execute.return_value = result_mock

        as_of = datetime(2024, 1, 15, tzinfo=UTC)
        result = pit_latest_ohlcv("BBCA", as_of, session)
        assert result is None

    def test_returns_row_dict(self) -> None:
        session = MagicMock()
        row = MagicMock()
        row._mapping = {
            "time": datetime(2024, 1, 14, tzinfo=UTC),
            "symbol": "BBCA",
            "open": 9000,
            "high": 9100,
            "low": 8950,
            "close": 9050,
            "volume": 1000000,
        }
        result_mock = MagicMock()
        result_mock.fetchone.return_value = row
        session.execute.return_value = result_mock

        as_of = datetime(2024, 1, 15, tzinfo=UTC)
        result = pit_latest_ohlcv("BBCA", as_of, session)
        assert result is not None
        assert result["symbol"] == "BBCA"
        assert result["close"] == 9050

    def test_future_as_of_raises(self) -> None:
        session = MagicMock()
        future = datetime.now(tz=UTC) + timedelta(hours=1)
        with pytest.raises(PyhronLookAheadError):
            pit_latest_ohlcv("BBCA", future, session)


class TestLookforwardLeakDetector:
    """Test look-ahead bias detection."""

    def test_suspicious_pattern_detected(self) -> None:
        assert lookforward_leak_detector(4.0, -0.5) is True

    def test_normal_pattern_not_flagged(self) -> None:
        assert lookforward_leak_detector(1.5, 0.8) is False

    def test_high_is_positive_oos_not_flagged(self) -> None:
        assert lookforward_leak_detector(4.0, 0.5) is False

    def test_low_is_negative_oos_not_flagged(self) -> None:
        assert lookforward_leak_detector(2.0, -0.5) is False

    def test_custom_threshold(self) -> None:
        assert lookforward_leak_detector(2.5, -0.1, sharpe_threshold=2.0) is True
