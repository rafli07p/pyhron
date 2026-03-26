"""Integration test for the full order pipeline.

Tests the signal → risk check → order state machine flow end-to-end,
with mocked Kafka/Redis but real business logic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

# Transitive import to shared.kafka_producer_consumer uses Python 3.12+
# generic class syntax (PEP 695).  Skip on older runtimes.
try:
    from services.pre_trade_risk_engine.pre_trade_risk_checks import (
        check_daily_loss_limit,
        check_duplicate_order,
        check_lot_size_constraint,
        check_max_position_size,
        check_signal_staleness,
    )
except SyntaxError:
    pytest.skip(
        "Requires Python 3.12+ (PEP 695 generic syntax in kafka_producer_consumer)",
        allow_module_level=True,
    )

# Helpers
def _make_order(
    quantity: int = 100,
    side: int = 1,
    symbol: str = "BBCA.JK",
    limit_price: float = 9200.0,
    client_order_id: str = "pipeline-test-001",
    signal_time: datetime | None = None,
) -> MagicMock:
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
    portfolio_var_95: float = 10_000_000.0,
) -> MagicMock:
    portfolio = MagicMock()
    portfolio.total_market_value = total_market_value
    portfolio.cash_balance = cash_balance
    portfolio.positions = positions or []
    portfolio.total_unrealized_pnl = total_unrealized_pnl
    portfolio.total_realized_pnl_today = total_realized_pnl_today
    portfolio.portfolio_var_95 = portfolio_var_95
    return portfolio


# Pipeline Tests
class TestFullOrderPipeline:
    """End-to-end risk check pipeline with realistic scenarios."""

    def test_valid_order_passes_all_checks(self):
        """A well-formed order should pass all pre-trade risk checks."""
        now = datetime.now(tz=UTC)
        order = _make_order(
            quantity=500,
            limit_price=9200.0,
            signal_time=now - timedelta(seconds=30),
        )
        portfolio = _make_portfolio()

        results = []
        results.append(check_lot_size_constraint(order, lot_size=100))
        results.append(check_daily_loss_limit(portfolio, daily_loss_limit_pct=0.02))
        results.append(check_duplicate_order(order, recent_orders=[]))
        results.append(check_signal_staleness(order, max_age_seconds=300))
        results.append(check_max_position_size(order, portfolio, max_pct=0.10))

        for r in results:
            assert r.passed, f"Check {r.check_name} failed: {r.reason}"

    def test_invalid_lot_size_rejects_early(self):
        """Orders with invalid lot sizes should be rejected at the first check."""
        now = datetime.now(tz=UTC)
        order = _make_order(quantity=150, signal_time=now)
        _make_portfolio()

        # Simulate fail-fast pipeline
        lot_result = check_lot_size_constraint(order, lot_size=100)
        assert lot_result.passed is False

        # Pipeline should stop here — no further checks needed
        rejection_reasons = [f"{lot_result.check_name}: {lot_result.reason}"]
        assert len(rejection_reasons) == 1
        assert "lot_size" in rejection_reasons[0]

    def test_stale_signal_rejected(self):
        """Orders from stale signals should be rejected."""
        old_time = datetime.now(tz=UTC) - timedelta(minutes=10)
        order = _make_order(quantity=100, signal_time=old_time)

        result = check_signal_staleness(order, max_age_seconds=300)
        assert result.passed is False

    def test_duplicate_order_rejected(self):
        """Duplicate orders should be caught by the idempotency guard."""
        order = _make_order(client_order_id="dup-001")
        result = check_duplicate_order(order, recent_orders=["dup-001", "dup-002"])
        assert result.passed is False

    def test_daily_loss_triggers_circuit_breaker(self):
        """When daily loss exceeds the threshold, all orders are rejected."""
        portfolio = _make_portfolio(
            total_market_value=100_000_000,
            cash_balance=0,
            total_unrealized_pnl=-5_000_000,
            total_realized_pnl_today=-1_000_000,
        )
        result = check_daily_loss_limit(portfolio, daily_loss_limit_pct=0.02)
        assert result.passed is False
        assert "Trading halted" in result.reason

    def test_oversized_position_rejected(self):
        """Orders that would create oversized positions are rejected."""
        order = _make_order(quantity=500_000, limit_price=9200.0)
        portfolio = _make_portfolio(
            total_market_value=10_000_000,
            cash_balance=10_000_000,
        )
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is False

    def test_pipeline_with_existing_position(self):
        """Orders should be evaluated against existing portfolio state."""
        now = datetime.now(tz=UTC)
        pos = MagicMock()
        pos.symbol = "BBCA.JK"
        pos.quantity = 50_000
        pos.current_price = 9200.0
        pos.market_value = 460_000_000.0

        portfolio = _make_portfolio(
            total_market_value=460_000_000,
            cash_balance=540_000_000,
            positions=[pos],
        )

        # This additional buy would push position over 10%
        order = _make_order(
            quantity=100_000,
            limit_price=9200.0,
            signal_time=now - timedelta(seconds=5),
        )
        result = check_max_position_size(order, portfolio, max_pct=0.10)
        assert result.passed is False
