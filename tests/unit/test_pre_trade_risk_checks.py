"""Unit tests for pre-trade risk checks from the pre_trade_risk_engine.

Tests position limits, concentration limits, and max order value.
All checks are pure functions -- only mock protobuf inputs.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.pre_trade_risk_engine.pre_trade_risk_checks import (
    RiskCheckResult,
    check_buying_power_t2,
    check_lot_size_constraint,
    check_max_position_size,
    check_sector_concentration,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_order(
    quantity: int = 100,
    side: int = 1,
    symbol: str = "BBCA.JK",
    limit_price: float = 9200.0,
    client_order_id: str = "test-order-001",
) -> MagicMock:
    order = MagicMock()
    order.quantity = quantity
    order.side = side
    order.symbol = symbol
    order.limit_price = limit_price
    order.client_order_id = client_order_id
    return order


def _make_portfolio(
    total_market_value: float = 1_000_000_000.0,
    cash_balance: float = 500_000_000.0,
    positions: list | None = None,
) -> MagicMock:
    portfolio = MagicMock()
    portfolio.total_market_value = total_market_value
    portfolio.cash_balance = cash_balance
    portfolio.positions = positions or []
    return portfolio


def _make_position(symbol: str, quantity: int, current_price: float, market_value: float) -> MagicMock:
    pos = MagicMock()
    pos.symbol = symbol
    pos.quantity = quantity
    pos.current_price = current_price
    pos.market_value = market_value
    return pos


# ── Position Limit Tests ────────────────────────────────────────────────────


class TestPositionLimits:
    """Test that position size checks enforce percentage limits."""

    def test_small_order_within_limit(self):
        order = _make_order(quantity=100, limit_price=9200.0)
        portfolio = _make_portfolio(total_market_value=1_000_000_000.0)
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is True

    def test_large_order_exceeds_position_limit(self):
        order = _make_order(quantity=100_000, limit_price=9200.0)
        portfolio = _make_portfolio(total_market_value=5_000_000.0, cash_balance=5_000_000.0)
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is False
        assert result.check_name == "max_position_size"

    def test_existing_position_counted(self):
        positions = [_make_position("BBCA.JK", 5000, 9200.0, 46_000_000.0)]
        order = _make_order(quantity=5000, limit_price=9200.0)
        portfolio = _make_portfolio(total_market_value=100_000_000.0, cash_balance=0, positions=positions)
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is False

    def test_sell_order_reduces_exposure(self):
        positions = [_make_position("BBCA.JK", 1000, 9200.0, 9_200_000.0)]
        order = _make_order(quantity=500, side=2, limit_price=9200.0)
        portfolio = _make_portfolio(total_market_value=100_000_000.0, cash_balance=0, positions=positions)
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is True


# ── Concentration Limit Tests ───────────────────────────────────────────────


class TestConcentrationLimits:
    """Test sector concentration checks."""

    def test_single_sector_within_limit(self):
        order = _make_order(quantity=100, limit_price=9200.0)
        portfolio = _make_portfolio()
        sector_map = {"BBCA.JK": "FINANCIALS"}
        result = check_sector_concentration(order, portfolio, sector_map, max_pct=0.30)
        assert result.passed is True

    def test_sector_exceeds_concentration_limit(self):
        positions = [
            _make_position("BBCA.JK", 10_000, 9200.0, 400_000_000.0),
            _make_position("BBRI.JK", 10_000, 5500.0, 300_000_000.0),
        ]
        order = _make_order(quantity=100_000, limit_price=9200.0)
        portfolio = _make_portfolio(total_market_value=1_000_000_000.0, cash_balance=500_000_000.0, positions=positions)
        sector_map = {"BBCA.JK": "FINANCIALS", "BBRI.JK": "FINANCIALS"}
        result = check_sector_concentration(order, portfolio, sector_map, max_pct=0.30)
        assert result.passed is False
        assert "FINANCIALS" in result.reason

    def test_unknown_sector_passes(self):
        order = _make_order(symbol="UNKNOWN.JK")
        portfolio = _make_portfolio()
        result = check_sector_concentration(order, portfolio, {}, max_pct=0.30)
        assert result.passed is True


# ── Max Order Value Tests ───────────────────────────────────────────────────


class TestMaxOrderValue:
    """Test buying power checks enforce maximum order value."""

    def test_order_within_buying_power(self):
        order = _make_order(quantity=100, limit_price=9200.0, side=1)
        result = check_buying_power_t2(order, available_cash=10_000_000.0, current_price=9200.0)
        assert result.passed is True

    def test_order_exceeds_buying_power(self):
        order = _make_order(quantity=10_000, limit_price=9200.0, side=1)
        result = check_buying_power_t2(order, available_cash=1_000_000.0, current_price=9200.0)
        assert result.passed is False
        assert "buying power" in result.reason.lower()

    def test_sell_order_bypasses_buying_power(self):
        order = _make_order(quantity=100, side=2)
        result = check_buying_power_t2(order, available_cash=0, current_price=9200.0)
        assert result.passed is True

    def test_lot_size_valid(self):
        order = _make_order(quantity=500)
        result = check_lot_size_constraint(order, lot_size=100)
        assert result.passed is True
        assert result.check_name == "lot_size"

    def test_lot_size_invalid_rounds_down(self):
        order = _make_order(quantity=250)
        result = check_lot_size_constraint(order, lot_size=100)
        assert result.passed is False
        assert result.adjusted_quantity == 200
