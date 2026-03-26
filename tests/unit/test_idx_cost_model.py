"""Unit tests for the IDX transaction cost model.

Validates buy/sell cost calculations, minimum commission,
breakeven return, and cost component accuracy for Indonesian
Stock Exchange transactions.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

try:
    from services.paper_trading.idx_cost_model import (
        IDXTransactionCostModel,
        TransactionCost,
    )
except ImportError:
    pytest.skip("Requires paper trading modules", allow_module_level=True)


@pytest.fixture
def model() -> IDXTransactionCostModel:
    return IDXTransactionCostModel()


class TestBuyCost:
    """Tests for buy-side transaction costs."""

    def test_standard_buy_cost(self, model: IDXTransactionCostModel) -> None:
        """Standard buy should apply 0.15% commission + levy + VAT."""
        value = Decimal("100000000")  # 100M IDR
        cost = model.compute_buy_cost(value)

        # Commission: 100M * 0.15% = 150,000
        assert cost.commission_idr == Decimal("150000")
        # IDX Levy: 100M * 0.01% = 10,000
        assert cost.idx_levy_idr == Decimal("10000")
        # VAT: 150,000 * 11% = 16,500
        assert cost.vat_idr == Decimal("16500")
        # No PPh on buy
        assert cost.pph_idr == Decimal("0")
        # Total: 150,000 + 10,000 + 16,500 = 176,500
        assert cost.total_cost_idr == Decimal("176500")

    def test_minimum_commission_applies(self, model: IDXTransactionCostModel) -> None:
        """Small transactions should use minimum commission IDR 10,000."""
        value = Decimal("1000000")  # 1M IDR
        cost = model.compute_buy_cost(value)

        # Commission: 1M * 0.15% = 1,500 -> min 10,000 applies
        assert cost.commission_idr == Decimal("10000")

    def test_buy_cost_components_sum(self, model: IDXTransactionCostModel) -> None:
        """Total cost should equal sum of components."""
        cost = model.compute_buy_cost(Decimal("50000000"))
        expected_total = cost.commission_idr + cost.idx_levy_idr + cost.vat_idr + cost.pph_idr
        assert cost.total_cost_idr == expected_total

    def test_effective_cost_pct(self, model: IDXTransactionCostModel) -> None:
        """Effective cost percentage should be roughly 0.17%."""
        cost = model.compute_buy_cost(Decimal("100000000"))
        assert Decimal("0.15") < cost.effective_cost_pct < Decimal("0.20")


class TestSellCost:
    """Tests for sell-side transaction costs."""

    def test_standard_sell_cost(self, model: IDXTransactionCostModel) -> None:
        """Standard sell should apply 0.25% commission + levy + VAT + PPh."""
        value = Decimal("100000000")  # 100M IDR
        cost = model.compute_sell_cost(value)

        # Commission: 100M * 0.25% = 250,000
        assert cost.commission_idr == Decimal("250000")
        # IDX Levy: 100M * 0.01% = 10,000
        assert cost.idx_levy_idr == Decimal("10000")
        # VAT: 250,000 * 11% = 27,500
        assert cost.vat_idr == Decimal("27500")
        # PPh: 100M * 0.10% = 100,000
        assert cost.pph_idr == Decimal("100000")
        # Total: 250,000 + 10,000 + 27,500 + 100,000 = 387,500
        assert cost.total_cost_idr == Decimal("387500")

    def test_sell_cost_higher_than_buy(self, model: IDXTransactionCostModel) -> None:
        """Sell cost should always exceed buy cost (PPh tax)."""
        value = Decimal("100000000")
        buy = model.compute_buy_cost(value)
        sell = model.compute_sell_cost(value)
        assert sell.total_cost_idr > buy.total_cost_idr

    def test_sell_has_pph(self, model: IDXTransactionCostModel) -> None:
        """Sell side should include PPh final tax."""
        cost = model.compute_sell_cost(Decimal("100000000"))
        assert cost.pph_idr > 0

    def test_sell_effective_cost_pct(self, model: IDXTransactionCostModel) -> None:
        """Sell effective cost should be roughly 0.39%."""
        cost = model.compute_sell_cost(Decimal("100000000"))
        assert Decimal("0.35") < cost.effective_cost_pct < Decimal("0.45")


class TestBreakevenReturn:
    """Tests for breakeven return calculation."""

    def test_breakeven_positive(self, model: IDXTransactionCostModel) -> None:
        """Breakeven return should be positive."""
        breakeven = model.compute_breakeven_return(Decimal("100000000"))
        assert breakeven > 0

    def test_breakeven_roughly_half_percent(self, model: IDXTransactionCostModel) -> None:
        """Round-trip cost should be roughly 0.55%."""
        breakeven = model.compute_breakeven_return(Decimal("100000000"))
        assert Decimal("0.004") < breakeven < Decimal("0.007")

    def test_breakeven_zero_value(self, model: IDXTransactionCostModel) -> None:
        """Zero transaction value should return zero breakeven."""
        breakeven = model.compute_breakeven_return(Decimal("0"))
        assert breakeven == Decimal("0")


class TestTransactionCostDataclass:
    """Tests for the TransactionCost dataclass."""

    def test_frozen(self) -> None:
        """TransactionCost should be immutable."""
        cost = TransactionCost(
            transaction_value_idr=Decimal("1000"),
            commission_idr=Decimal("10"),
            idx_levy_idr=Decimal("1"),
            vat_idr=Decimal("1"),
            pph_idr=Decimal("0"),
            total_cost_idr=Decimal("12"),
            effective_cost_pct=Decimal("1.2"),
        )
        with pytest.raises(AttributeError):
            cost.commission_idr = Decimal("999")  # type: ignore[misc]
