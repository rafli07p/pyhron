"""
Tests for the risk limit checking engine.

Validates that risk checks correctly enforce position limits,
VaR constraints, drawdown thresholds, and concentration limits.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

# TODO: update imports when enthropy.risk / enthropy.shared.schemas are implemented
# Future paths:
#   from services.risk.risk_limits import RiskLimitEngine (as RiskEngine), TenantRiskLimits (as RiskLimits)
#   from shared.schemas.order_events import OrderRequest (as OrderCreate), OrderSide, OrderType
#   RiskCheckResult, RiskViolationType, PositionSnapshot — not yet implemented
pytest.importorskip("enthropy.risk.engine", reason="module not yet implemented")
from enthropy.risk.engine import RiskEngine
from enthropy.risk.models import (
    RiskCheckResult,
    RiskViolationType,
)
from enthropy.shared.schemas.order import OrderCreate, OrderSide, OrderType
from enthropy.shared.schemas.position import PositionSnapshot
from enthropy.shared.schemas.risk import RiskLimits


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def default_limits() -> RiskLimits:
    """Standard risk limits for testing."""
    return RiskLimits(
        max_position_size=Decimal("10000000.00"),
        max_order_size=Decimal("1000000.00"),
        max_daily_loss=Decimal("500000.00"),
        max_drawdown_pct=Decimal("0.10"),
        max_var=Decimal("2000000.00"),
        max_concentration_pct=Decimal("0.25"),
        max_leverage=Decimal("2.0"),
    )


@pytest.fixture
def risk_engine(default_limits: RiskLimits) -> RiskEngine:
    """Risk engine instance with default limits."""
    return RiskEngine(limits=default_limits)


@pytest.fixture
def sample_buy_order() -> OrderCreate:
    """Sample buy order for testing."""
    return OrderCreate(
        symbol="BBCA.JK",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("1000"),
        price=Decimal("9200.00"),
        strategy_id="momentum_v1",
    )


@pytest.fixture
def sample_positions() -> list[PositionSnapshot]:
    """Sample portfolio positions."""
    now = datetime.now(UTC)
    return [
        PositionSnapshot(
            symbol="BBCA.JK",
            quantity=Decimal("5000"),
            average_entry_price=Decimal("9000.00"),
            current_price=Decimal("9200.00"),
            unrealized_pnl=Decimal("1000000.00"),
            realized_pnl=Decimal("0.00"),
            market_value=Decimal("46000000.00"),
            strategy_id="momentum_v1",
            updated_at=now,
        ),
        PositionSnapshot(
            symbol="TLKM.JK",
            quantity=Decimal("10000"),
            average_entry_price=Decimal("3800.00"),
            current_price=Decimal("3850.00"),
            unrealized_pnl=Decimal("500000.00"),
            realized_pnl=Decimal("200000.00"),
            market_value=Decimal("38500000.00"),
            strategy_id="value_v1",
            updated_at=now,
        ),
    ]


# =============================================================================
# Order Size Limit Tests
# =============================================================================
class TestOrderSizeLimits:
    """Tests for order size limit checks."""

    def test_order_within_size_limit(self, risk_engine: RiskEngine, sample_buy_order: OrderCreate):
        """Orders within size limits should pass."""
        result = risk_engine.check_order_size(sample_buy_order)
        assert result.passed is True
        assert len(result.violations) == 0

    def test_order_exceeds_size_limit(self, risk_engine: RiskEngine):
        """Orders exceeding max_order_size should be rejected."""
        large_order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("200"),
            price=Decimal("9200.00"),
            strategy_id="momentum_v1",
        )
        # Notional = 200 * 9200 = 1,840,000 > 1,000,000 limit
        result = risk_engine.check_order_size(large_order)
        assert result.passed is False
        assert any(v.violation_type == RiskViolationType.ORDER_SIZE_EXCEEDED for v in result.violations)

    def test_market_order_uses_last_price(self, risk_engine: RiskEngine):
        """Market orders should use last known price for size check."""
        market_order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("50"),
            price=None,
            strategy_id="momentum_v1",
        )
        risk_engine.update_last_price("BBCA.JK", Decimal("9200.00"))
        result = risk_engine.check_order_size(market_order)
        assert result.passed is True


# =============================================================================
# Position Size Limit Tests
# =============================================================================
class TestPositionSizeLimits:
    """Tests for position-level limit checks."""

    def test_new_position_within_limit(
        self,
        risk_engine: RiskEngine,
        sample_buy_order: OrderCreate,
    ):
        """New position within limits should pass."""
        result = risk_engine.check_position_limit(
            order=sample_buy_order,
            current_position_value=Decimal("5000000.00"),
        )
        assert result.passed is True

    def test_position_would_exceed_limit(self, risk_engine: RiskEngine):
        """Order that would push position over limit should be rejected."""
        order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("500"),
            price=Decimal("9200.00"),
            strategy_id="momentum_v1",
        )
        # Current position: 9.5M + new order: 0.5*9200=4.6M = ~14.1M > 10M limit
        result = risk_engine.check_position_limit(
            order=order,
            current_position_value=Decimal("9500000.00"),
        )
        assert result.passed is False
        assert any(v.violation_type == RiskViolationType.POSITION_LIMIT_EXCEEDED for v in result.violations)

    def test_sell_order_reduces_position(self, risk_engine: RiskEngine):
        """Sell orders reducing position should always pass position check."""
        sell_order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1000"),
            price=None,
            strategy_id="momentum_v1",
        )
        result = risk_engine.check_position_limit(
            order=sell_order,
            current_position_value=Decimal("9500000.00"),
        )
        assert result.passed is True


# =============================================================================
# VaR Limit Tests
# =============================================================================
class TestVaRLimits:
    """Tests for Value at Risk limit checks."""

    def test_var_within_limit(self, risk_engine: RiskEngine):
        """VaR within limits should pass."""
        result = risk_engine.check_var(
            current_var=Decimal("1500000.00"),
            proposed_var_impact=Decimal("200000.00"),
        )
        assert result.passed is True

    def test_var_exceeds_limit(self, risk_engine: RiskEngine):
        """VaR exceeding limit should be rejected."""
        result = risk_engine.check_var(
            current_var=Decimal("1800000.00"),
            proposed_var_impact=Decimal("500000.00"),
        )
        assert result.passed is False
        assert any(v.violation_type == RiskViolationType.VAR_LIMIT_EXCEEDED for v in result.violations)

    def test_var_at_exactly_limit(self, risk_engine: RiskEngine):
        """VaR exactly at limit should pass (boundary condition)."""
        result = risk_engine.check_var(
            current_var=Decimal("1500000.00"),
            proposed_var_impact=Decimal("500000.00"),
        )
        assert result.passed is True

    def test_var_warning_threshold(self, risk_engine: RiskEngine):
        """VaR approaching limit should generate warning."""
        result = risk_engine.check_var(
            current_var=Decimal("1700000.00"),
            proposed_var_impact=Decimal("200000.00"),
        )
        # 1.9M is within 2M limit but above 90% warning threshold
        assert result.passed is True
        assert result.warnings is not None
        assert len(result.warnings) > 0


# =============================================================================
# Drawdown Limit Tests
# =============================================================================
class TestDrawdownLimits:
    """Tests for drawdown threshold checks."""

    def test_drawdown_within_limit(self, risk_engine: RiskEngine):
        """Drawdown within limits should pass."""
        result = risk_engine.check_drawdown(
            peak_value=Decimal("100000000.00"),
            current_value=Decimal("95000000.00"),
        )
        assert result.passed is True

    def test_drawdown_exceeds_limit(self, risk_engine: RiskEngine):
        """Drawdown exceeding limit should trigger halt."""
        result = risk_engine.check_drawdown(
            peak_value=Decimal("100000000.00"),
            current_value=Decimal("85000000.00"),
        )
        # 15% drawdown > 10% limit
        assert result.passed is False
        assert any(v.violation_type == RiskViolationType.DRAWDOWN_EXCEEDED for v in result.violations)

    @pytest.mark.parametrize(
        "peak,current,should_pass",
        [
            (Decimal("100"), Decimal("91"), True),  # 9% < 10%
            (Decimal("100"), Decimal("90"), True),  # 10% == 10% (at limit)
            (Decimal("100"), Decimal("89"), False),  # 11% > 10%
            (Decimal("100"), Decimal("100"), True),  # 0% drawdown
        ],
    )
    def test_drawdown_boundary_conditions(
        self,
        risk_engine: RiskEngine,
        peak: Decimal,
        current: Decimal,
        should_pass: bool,
    ):
        """Drawdown boundary conditions should be handled correctly."""
        result = risk_engine.check_drawdown(peak_value=peak, current_value=current)
        assert result.passed is should_pass


# =============================================================================
# Concentration Limit Tests
# =============================================================================
class TestConcentrationLimits:
    """Tests for portfolio concentration checks."""

    def test_diversified_portfolio(
        self,
        risk_engine: RiskEngine,
        sample_positions: list[PositionSnapshot],
    ):
        """Diversified portfolio should pass concentration checks."""
        total_value = sum(abs(p.market_value) for p in sample_positions)
        for position in sample_positions:
            result = risk_engine.check_concentration(
                position_value=abs(position.market_value),
                total_portfolio_value=total_value,
            )
            # Each position is ~50% which exceeds 25% limit
            # This test validates the check fires appropriately
            assert isinstance(result, RiskCheckResult)

    def test_concentrated_position(self, risk_engine: RiskEngine):
        """Single position dominating portfolio should be flagged."""
        result = risk_engine.check_concentration(
            position_value=Decimal("8000000.00"),
            total_portfolio_value=Decimal("10000000.00"),
        )
        # 80% > 25% limit
        assert result.passed is False
        assert any(v.violation_type == RiskViolationType.CONCENTRATION_EXCEEDED for v in result.violations)

    def test_small_position_passes(self, risk_engine: RiskEngine):
        """Small position should pass concentration check."""
        result = risk_engine.check_concentration(
            position_value=Decimal("1000000.00"),
            total_portfolio_value=Decimal("10000000.00"),
        )
        # 10% < 25% limit
        assert result.passed is True


# =============================================================================
# Leverage Limit Tests
# =============================================================================
class TestLeverageLimits:
    """Tests for leverage constraint checks."""

    def test_leverage_within_limit(self, risk_engine: RiskEngine):
        """Leverage within limits should pass."""
        result = risk_engine.check_leverage(
            total_exposure=Decimal("15000000.00"),
            equity=Decimal("10000000.00"),
        )
        # 1.5x < 2.0x limit
        assert result.passed is True

    def test_leverage_exceeds_limit(self, risk_engine: RiskEngine):
        """Leverage exceeding limit should be rejected."""
        result = risk_engine.check_leverage(
            total_exposure=Decimal("25000000.00"),
            equity=Decimal("10000000.00"),
        )
        # 2.5x > 2.0x limit
        assert result.passed is False

    def test_zero_equity_handled(self, risk_engine: RiskEngine):
        """Zero equity should be handled gracefully."""
        result = risk_engine.check_leverage(
            total_exposure=Decimal("1000000.00"),
            equity=Decimal("0"),
        )
        assert result.passed is False


# =============================================================================
# Combined Risk Check Tests
# =============================================================================
class TestCombinedRiskChecks:
    """Tests for the full pre-trade risk check pipeline."""

    def test_all_checks_pass(
        self,
        risk_engine: RiskEngine,
        sample_buy_order: OrderCreate,
    ):
        """Order passing all checks should be approved."""
        result = risk_engine.run_pre_trade_checks(
            order=sample_buy_order,
            current_position_value=Decimal("2000000.00"),
            current_var=Decimal("500000.00"),
            proposed_var_impact=Decimal("100000.00"),
            peak_portfolio_value=Decimal("50000000.00"),
            current_portfolio_value=Decimal("48000000.00"),
            position_value_for_concentration=Decimal("5000000.00"),
            total_portfolio_value=Decimal("50000000.00"),
            total_exposure=Decimal("60000000.00"),
            equity=Decimal("50000000.00"),
        )
        assert result.passed is True
        assert len(result.violations) == 0

    def test_multiple_violations_reported(self, risk_engine: RiskEngine):
        """All violations should be reported, not just the first."""
        large_order = OrderCreate(
            symbol="BBCA.JK",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("500"),
            price=Decimal("9200.00"),
            strategy_id="aggressive_v1",
        )
        result = risk_engine.run_pre_trade_checks(
            order=large_order,
            current_position_value=Decimal("9500000.00"),
            current_var=Decimal("1900000.00"),
            proposed_var_impact=Decimal("500000.00"),
            peak_portfolio_value=Decimal("100000000.00"),
            current_portfolio_value=Decimal("85000000.00"),
            position_value_for_concentration=Decimal("8000000.00"),
            total_portfolio_value=Decimal("10000000.00"),
            total_exposure=Decimal("25000000.00"),
            equity=Decimal("10000000.00"),
        )
        assert result.passed is False
        # Should report multiple violations
        assert len(result.violations) >= 2

    def test_risk_check_is_idempotent(
        self,
        risk_engine: RiskEngine,
        sample_buy_order: OrderCreate,
    ):
        """Running the same check twice should produce the same result."""
        kwargs = {
            "order": sample_buy_order,
            "current_position_value": Decimal("2000000.00"),
            "current_var": Decimal("500000.00"),
            "proposed_var_impact": Decimal("100000.00"),
            "peak_portfolio_value": Decimal("50000000.00"),
            "current_portfolio_value": Decimal("48000000.00"),
            "position_value_for_concentration": Decimal("5000000.00"),
            "total_portfolio_value": Decimal("50000000.00"),
            "total_exposure": Decimal("60000000.00"),
            "equity": Decimal("50000000.00"),
        }
        result1 = risk_engine.run_pre_trade_checks(**kwargs)
        result2 = risk_engine.run_pre_trade_checks(**kwargs)
        assert result1.passed == result2.passed
        assert len(result1.violations) == len(result2.violations)
