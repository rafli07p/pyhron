"""Unit tests for pre-trade risk checks.

All checks are pure functions — no mocking required for the checks themselves.
We only mock protobuf objects to provide test inputs.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from services.pre_trade_risk_engine.pre_trade_risk_checks import (
    check_buying_power_t2,
    check_daily_loss_limit,
    check_duplicate_order,
    check_lot_size_constraint,
    check_max_position_size,
    check_portfolio_var,
    check_sector_concentration,
    check_signal_staleness,
)


# Helpers
def _make_order(
    quantity: int = 100,
    side: int = 1,  # BUY
    symbol: str = "BBCA.JK",
    limit_price: float = 9200.0,
    client_order_id: str = "test-order-001",
    signal_time: datetime | None = None,
) -> MagicMock:
    """Create a mock OrderRequest protobuf."""
    order = MagicMock()
    order.quantity = quantity
    order.side = side
    order.symbol = symbol
    order.limit_price = limit_price
    order.client_order_id = client_order_id

    if signal_time is not None:
        order.HasField.return_value = True
        order.signal_time.ToDatetime.return_value = signal_time.replace(tzinfo=None)
    else:
        order.HasField.return_value = False

    return order


def _make_portfolio(
    total_market_value: float = 1_000_000_000.0,
    cash_balance: float = 500_000_000.0,
    positions: list | None = None,
    total_unrealized_pnl: float = 0.0,
    total_realized_pnl_today: float = 0.0,
    portfolio_var_95: float = 0.0,
) -> MagicMock:
    """Create a mock PortfolioSnapshot protobuf."""
    portfolio = MagicMock()
    portfolio.total_market_value = total_market_value
    portfolio.cash_balance = cash_balance
    portfolio.positions = positions or []
    portfolio.total_unrealized_pnl = total_unrealized_pnl
    portfolio.total_realized_pnl_today = total_realized_pnl_today
    portfolio.portfolio_var_95 = portfolio_var_95
    return portfolio


def _make_position(
    symbol: str = "BBCA.JK",
    quantity: int = 1000,
    current_price: float = 9200.0,
    market_value: float = 9_200_000.0,
) -> MagicMock:
    pos = MagicMock()
    pos.symbol = symbol
    pos.quantity = quantity
    pos.current_price = current_price
    pos.market_value = market_value
    return pos


# Lot Size
class TestLotSizeConstraint:
    def test_valid_lot_size(self):
        order = _make_order(quantity=500)
        result = check_lot_size_constraint(order, lot_size=100)
        assert result.passed is True
        assert result.check_name == "lot_size"

    def test_invalid_lot_size(self):
        order = _make_order(quantity=150)
        result = check_lot_size_constraint(order, lot_size=100)
        assert result.passed is False
        assert "not a multiple" in result.reason
        assert result.adjusted_quantity == 100

    def test_zero_quantity(self):
        order = _make_order(quantity=0)
        result = check_lot_size_constraint(order, lot_size=100)
        assert result.passed is False
        assert "positive" in result.reason

    def test_negative_quantity(self):
        order = _make_order(quantity=-100)
        result = check_lot_size_constraint(order, lot_size=100)
        assert result.passed is False

    def test_minimum_lot(self):
        order = _make_order(quantity=100)
        result = check_lot_size_constraint(order, lot_size=100)
        assert result.passed is True

    def test_adjusted_quantity_rounds_down(self):
        order = _make_order(quantity=250)
        result = check_lot_size_constraint(order, lot_size=100)
        assert result.adjusted_quantity == 200

    def test_sub_lot_adjusted_to_none(self):
        order = _make_order(quantity=50)
        result = check_lot_size_constraint(order, lot_size=100)
        assert result.passed is False
        assert result.adjusted_quantity is None


# Max Position Size
class TestMaxPositionSize:
    def test_within_limit(self):
        order = _make_order(quantity=100, limit_price=9200.0)
        portfolio = _make_portfolio(total_market_value=1_000_000_000.0)
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is True

    def test_exceeds_limit(self):
        order = _make_order(quantity=100_000, limit_price=9200.0)
        portfolio = _make_portfolio(total_market_value=5_000_000.0, cash_balance=5_000_000.0)
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is False
        assert result.check_name == "max_position_size"

    def test_zero_portfolio_value(self):
        order = _make_order(quantity=100)
        portfolio = _make_portfolio(total_market_value=0, cash_balance=0)
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is False
        assert "zero or negative" in result.reason

    def test_no_price_available(self):
        order = _make_order(quantity=100, limit_price=0)
        portfolio = _make_portfolio()
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is True
        assert "no price" in result.reason.lower()


# Daily Loss Limit
class TestDailyLossLimit:
    def test_no_loss(self):
        portfolio = _make_portfolio(total_unrealized_pnl=0, total_realized_pnl_today=0)
        result = check_daily_loss_limit(portfolio, daily_loss_limit_pct=0.02)
        assert result.passed is True

    def test_loss_within_limit(self):
        portfolio = _make_portfolio(
            total_unrealized_pnl=-10_000_000,
            total_realized_pnl_today=0,
        )
        result = check_daily_loss_limit(portfolio, daily_loss_limit_pct=0.02)
        assert result.passed is True  # -10M / 1.5B < 2%

    def test_loss_exceeds_limit(self):
        portfolio = _make_portfolio(
            total_market_value=100_000_000,
            cash_balance=0,
            total_unrealized_pnl=-3_000_000,
            total_realized_pnl_today=0,
        )
        result = check_daily_loss_limit(portfolio, daily_loss_limit_pct=0.02)
        assert result.passed is False
        assert "Trading halted" in result.reason

    def test_zero_portfolio_triggers_circuit_breaker(self):
        portfolio = _make_portfolio(total_market_value=0, cash_balance=0)
        result = check_daily_loss_limit(portfolio, daily_loss_limit_pct=0.02)
        assert result.passed is False


# Buying Power T+2
class TestBuyingPowerT2:
    def test_sufficient_cash(self):
        order = _make_order(quantity=100, limit_price=9200.0, side=1)
        result = check_buying_power_t2(order, available_cash=1_000_000.0, current_price=9200.0)
        assert result.passed is True

    def test_insufficient_cash(self):
        order = _make_order(quantity=1000, limit_price=9200.0, side=1)
        result = check_buying_power_t2(order, available_cash=1_000.0, current_price=9200.0)
        assert result.passed is False
        assert "buying power" in result.reason.lower()

    def test_sell_orders_pass(self):
        order = _make_order(quantity=100, side=2)  # SELL
        result = check_buying_power_t2(order, available_cash=0, current_price=9200.0)
        assert result.passed is True


# Duplicate Order
class TestDuplicateOrder:
    def test_no_duplicate(self):
        order = _make_order(client_order_id="order-new")
        result = check_duplicate_order(order, recent_orders=["order-1", "order-2"])
        assert result.passed is True

    def test_duplicate_detected(self):
        order = _make_order(client_order_id="order-1")
        result = check_duplicate_order(order, recent_orders=["order-1", "order-2"])
        assert result.passed is False
        assert "Duplicate" in result.reason

    def test_empty_recent_orders(self):
        order = _make_order(client_order_id="order-1")
        result = check_duplicate_order(order, recent_orders=[])
        assert result.passed is True


# Signal Staleness
class TestSignalStaleness:
    def test_fresh_signal(self):
        now = datetime.now(tz=UTC)
        order = _make_order(signal_time=now - timedelta(seconds=10))
        result = check_signal_staleness(order, max_age_seconds=300)
        assert result.passed is True

    def test_stale_signal(self):
        now = datetime.now(tz=UTC)
        order = _make_order(signal_time=now - timedelta(seconds=600))
        result = check_signal_staleness(order, max_age_seconds=300)
        assert result.passed is False
        assert "exceeds max" in result.reason

    def test_no_signal_time(self):
        order = _make_order(signal_time=None)
        result = check_signal_staleness(order, max_age_seconds=300)
        assert result.passed is False
        assert "no signal_time" in result.reason


# Portfolio VaR
class TestPortfolioVaR:
    def test_within_var_limit(self):
        order = _make_order(quantity=100, limit_price=9200.0)
        portfolio = _make_portfolio(portfolio_var_95=10_000_000.0)
        result = check_portfolio_var(order, portfolio, var_limit_pct=0.05)
        assert result.passed is True

    def test_exceeds_var_limit(self):
        order = _make_order(quantity=100_000, limit_price=9200.0)
        portfolio = _make_portfolio(
            total_market_value=10_000_000,
            cash_balance=0,
            portfolio_var_95=400_000,
        )
        result = check_portfolio_var(order, portfolio, var_limit_pct=0.05)
        assert result.passed is False
        assert "VaR" in result.reason

    def test_zero_portfolio_passes(self):
        order = _make_order(quantity=100)
        portfolio = _make_portfolio(total_market_value=0, cash_balance=0)
        result = check_portfolio_var(order, portfolio, var_limit_pct=0.05)
        assert result.passed is True


# Sector Concentration
class TestSectorConcentration:
    def test_within_limit(self):
        order = _make_order(quantity=100, limit_price=9200.0)
        portfolio = _make_portfolio()
        sector_map = {"BBCA.JK": "FINANCIALS"}
        result = check_sector_concentration(order, portfolio, sector_map, max_pct=0.30)
        assert result.passed is True

    def test_unknown_sector_passes(self):
        order = _make_order(symbol="UNKNOWN.JK")
        portfolio = _make_portfolio()
        sector_map = {"BBCA.JK": "FINANCIALS"}
        result = check_sector_concentration(order, portfolio, sector_map, max_pct=0.30)
        assert result.passed is True

    def test_exceeds_sector_limit(self):
        positions = [
            _make_position(symbol="BBCA.JK", market_value=400_000_000),
            _make_position(symbol="BBRI.JK", market_value=300_000_000),
        ]
        order = _make_order(quantity=100_000, limit_price=9200.0)
        portfolio = _make_portfolio(
            total_market_value=1_000_000_000,
            cash_balance=500_000_000,
            positions=positions,
        )
        sector_map = {"BBCA.JK": "FINANCIALS", "BBRI.JK": "FINANCIALS"}
        result = check_sector_concentration(order, portfolio, sector_map, max_pct=0.30)
        assert result.passed is False
        assert "FINANCIALS" in result.reason
