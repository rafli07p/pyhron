"""Unit tests for the IDX order validator.

Validates Indonesia Stock Exchange specific rules: lot size,
no naked short selling, tick size conformance, and price floor.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

try:
    from services.order_management_system.idx_order_validator import (
        IDX_MIN_PRICE_IDR,
        IDXOrderValidationResult,
        IDXOrderValidator,
    )
except ImportError:
    pytest.skip("Requires OMS modules", allow_module_level=True)


@pytest.fixture
def validator() -> IDXOrderValidator:
    return IDXOrderValidator()


class TestIDXLotValidation:
    """Tests for lot quantity validation."""

    def test_valid_lot_quantity(self, validator: IDXOrderValidator) -> None:
        """Positive lot quantity should pass."""
        result = validator.validate("BBCA.JK", "BUY", 10, "LIMIT", Decimal("9200"), 0)
        assert result.is_valid is True
        assert result.errors == []

    def test_zero_lot_quantity_rejected(self, validator: IDXOrderValidator) -> None:
        """Zero lot quantity should be rejected."""
        result = validator.validate("BBCA.JK", "BUY", 0, "LIMIT", Decimal("9200"), 0)
        assert result.is_valid is False
        assert any("positive" in e for e in result.errors)

    def test_negative_lot_quantity_rejected(self, validator: IDXOrderValidator) -> None:
        """Negative lot quantity should be rejected."""
        result = validator.validate("BBCA.JK", "BUY", -5, "LIMIT", Decimal("9200"), 0)
        assert result.is_valid is False


class TestIDXShortSellingRules:
    """Tests for no naked short selling rule (POJK No. 6/POJK.04/2015)."""

    def test_sell_within_position(self, validator: IDXOrderValidator) -> None:
        """Selling within current position should pass."""
        result = validator.validate("BBCA.JK", "SELL", 5, "MARKET", None, 10)
        assert result.is_valid is True

    def test_sell_exact_position(self, validator: IDXOrderValidator) -> None:
        """Selling exact position should pass."""
        result = validator.validate("BBCA.JK", "SELL", 10, "MARKET", None, 10)
        assert result.is_valid is True

    def test_sell_exceeds_position_rejected(self, validator: IDXOrderValidator) -> None:
        """Selling more than position should be rejected."""
        result = validator.validate("BBCA.JK", "SELL", 15, "MARKET", None, 10)
        assert result.is_valid is False
        assert any("short selling" in e.lower() for e in result.errors)

    def test_sell_with_zero_position_rejected(self, validator: IDXOrderValidator) -> None:
        """Selling with no position should be rejected."""
        result = validator.validate("BBCA.JK", "SELL", 1, "MARKET", None, 0)
        assert result.is_valid is False

    def test_buy_not_affected_by_short_rule(self, validator: IDXOrderValidator) -> None:
        """Buy orders should not be subject to short selling rule."""
        result = validator.validate("BBCA.JK", "BUY", 100, "LIMIT", Decimal("9200"), 0)
        assert result.is_valid is True


class TestIDXTickSize:
    """Tests for tick size conformance (Peraturan BEI No. II-A)."""

    @pytest.mark.parametrize(
        "price,expected_valid",
        [
            (Decimal("100"), True),    # tick=1, 100%1=0
            (Decimal("200"), True),    # tick=2, 200%2=0
            (Decimal("201"), False),   # tick=2, 201%2=1
            (Decimal("500"), True),    # tick=5, 500%5=0
            (Decimal("503"), False),   # tick=5, 503%5=3
            (Decimal("2000"), True),   # tick=10, 2000%10=0
            (Decimal("2005"), False),  # tick=10, 2005%10=5
            (Decimal("5000"), True),   # tick=25, 5000%25=0
            (Decimal("5010"), False),  # tick=25, 5010%25=10
        ],
    )
    def test_tick_conformance(
        self, validator: IDXOrderValidator, price: Decimal, expected_valid: bool
    ) -> None:
        """Prices should conform to IDX tick size for their tier."""
        result = validator.validate("BBCA.JK", "BUY", 1, "LIMIT", price, 0)
        if expected_valid:
            assert len(result.warnings) == 0
        else:
            assert any("tick size" in w.lower() for w in result.warnings)
        # Tick size is a warning, not an error
        assert result.is_valid is True

    def test_market_order_skips_tick_check(self, validator: IDXOrderValidator) -> None:
        """Market orders should not check tick size."""
        result = validator.validate("BBCA.JK", "BUY", 1, "MARKET", None, 0)
        assert result.is_valid is True
        assert result.warnings == []


class TestIDXPriceFloor:
    """Tests for minimum price validation."""

    def test_price_at_minimum(self, validator: IDXOrderValidator) -> None:
        """Price at IDX minimum should pass."""
        result = validator.validate("BBCA.JK", "BUY", 1, "LIMIT", IDX_MIN_PRICE_IDR, 0)
        assert result.is_valid is True

    def test_price_below_minimum_rejected(self, validator: IDXOrderValidator) -> None:
        """Price below IDX minimum should be rejected."""
        result = validator.validate("BBCA.JK", "BUY", 1, "LIMIT", Decimal("0"), 0)
        assert result.is_valid is False
        assert any("below" in e.lower() or "minimum" in e.lower() for e in result.errors)

    def test_negative_price_rejected(self, validator: IDXOrderValidator) -> None:
        """Negative price should be rejected."""
        result = validator.validate("BBCA.JK", "BUY", 1, "LIMIT", Decimal("-100"), 0)
        assert result.is_valid is False


class TestIDXValidationResult:
    """Tests for the validation result dataclass."""

    def test_valid_result(self) -> None:
        """Valid result should have is_valid=True and empty errors."""
        result = IDXOrderValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_with_errors(self) -> None:
        """Invalid result should carry error messages."""
        result = IDXOrderValidationResult(
            is_valid=False, errors=["too large"], warnings=["may be rounded"]
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_multiple_errors_accumulated(self, validator: IDXOrderValidator) -> None:
        """Multiple violations should all be reported."""
        result = validator.validate("BBCA.JK", "SELL", -1, "LIMIT", Decimal("0"), 0)
        assert result.is_valid is False
        assert len(result.errors) >= 2  # negative qty + price below minimum
