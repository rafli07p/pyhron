"""Unit tests for paper trading data models.

Validates DaySimulationResult, PaperSessionMetrics, and
AttributionReport dataclasses.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

try:
    from services.paper_trading.pnl_attribution import (
        AttributionReport,
        PaperSessionMetrics,
    )
    from services.paper_trading.simulation_engine import DaySimulationResult
except ImportError:
    pytest.skip("Requires paper trading modules", allow_module_level=True)


class TestDaySimulationResult:
    """Tests for DaySimulationResult dataclass."""

    def test_creation(self) -> None:
        """Should create result with all fields."""
        result = DaySimulationResult(
            trade_date=date(2025, 3, 3),
            signals_consumed=10,
            orders_filled=8,
            orders_unfilled=2,
            daily_pnl_idr=Decimal("1500000"),
            nav_idr=Decimal("1001500000"),
            cash_idr=Decimal("500000000"),
            turnover_idr=Decimal("50000000"),
        )
        assert result.trade_date == date(2025, 3, 3)
        assert result.signals_consumed == 10
        assert result.orders_filled == 8
        assert result.orders_unfilled == 2
        assert result.daily_pnl_idr == Decimal("1500000")

    def test_zero_activity_day(self) -> None:
        """Day with no signals should be representable."""
        result = DaySimulationResult(
            trade_date=date(2025, 3, 3),
            signals_consumed=0,
            orders_filled=0,
            orders_unfilled=0,
            daily_pnl_idr=Decimal("0"),
            nav_idr=Decimal("1000000000"),
            cash_idr=Decimal("1000000000"),
            turnover_idr=Decimal("0"),
        )
        assert result.orders_filled == 0


class TestPaperSessionMetrics:
    """Tests for PaperSessionMetrics dataclass."""

    def test_creation_with_all_metrics(self) -> None:
        """Should create metrics with all performance measures."""
        metrics = PaperSessionMetrics(
            sharpe_ratio=1.25,
            sortino_ratio=1.80,
            calmar_ratio=2.50,
            max_drawdown_pct=5.0,
            annualized_return_pct=12.5,
        )
        assert metrics.sharpe_ratio == 1.25
        assert metrics.sortino_ratio == 1.80
        assert metrics.max_drawdown_pct == 5.0

    def test_creation_with_none_ratios(self) -> None:
        """Should allow None for ratios when insufficient data."""
        metrics = PaperSessionMetrics(
            sharpe_ratio=None,
            sortino_ratio=None,
            calmar_ratio=None,
            max_drawdown_pct=0.0,
            annualized_return_pct=0.0,
        )
        assert metrics.sharpe_ratio is None

    def test_daily_returns_defaults_empty(self) -> None:
        """Daily returns should default to empty list."""
        metrics = PaperSessionMetrics(
            sharpe_ratio=None,
            sortino_ratio=None,
            calmar_ratio=None,
            max_drawdown_pct=0.0,
            annualized_return_pct=0.0,
        )
        assert metrics.daily_returns == []
        assert metrics.nav_series == []


class TestAttributionReport:
    """Tests for AttributionReport dataclass."""

    def test_creation(self) -> None:
        """Should create report with all fields."""
        report = AttributionReport(
            session_id="sess-001",
            date_from=date(2025, 1, 1),
            date_to=date(2025, 3, 31),
            total_realized_pnl_idr=Decimal("5000000"),
            total_unrealized_pnl_idr=Decimal("2000000"),
            total_commission_idr=Decimal("500000"),
            total_turnover_idr=Decimal("100000000"),
            total_trades=150,
        )
        assert report.session_id == "sess-001"
        assert report.total_trades == 150

    def test_symbol_attribution(self) -> None:
        """By-symbol attribution should be storable."""
        report = AttributionReport(
            session_id="sess-002",
            date_from=date(2025, 1, 1),
            date_to=date(2025, 3, 31),
            total_realized_pnl_idr=Decimal("5000000"),
            total_unrealized_pnl_idr=Decimal("2000000"),
            total_commission_idr=Decimal("500000"),
            total_turnover_idr=Decimal("100000000"),
            total_trades=150,
            by_symbol={
                "BBCA.JK": {"pnl": "3000000", "trades": 50},
                "TLKM.JK": {"pnl": "2000000", "trades": 100},
            },
        )
        assert "BBCA.JK" in report.by_symbol
        assert len(report.by_symbol) == 2

    def test_defaults_empty_dicts(self) -> None:
        """Attribution dicts should default to empty."""
        report = AttributionReport(
            session_id="sess-003",
            date_from=date(2025, 1, 1),
            date_to=date(2025, 3, 31),
            total_realized_pnl_idr=Decimal("0"),
            total_unrealized_pnl_idr=Decimal("0"),
            total_commission_idr=Decimal("0"),
            total_turnover_idr=Decimal("0"),
            total_trades=0,
        )
        assert report.by_symbol == {}
        assert report.by_signal_source == {}
