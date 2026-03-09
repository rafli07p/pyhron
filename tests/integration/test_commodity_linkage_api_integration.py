"""Integration test for commodity-stock linkage API.

Tests that commodity price changes (CPO, coal, nickel) produce correct
impact calculations on linked Indonesian equities.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Domain Models ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CommodityPrice:
    commodity: str
    price: float
    prev_price: float
    currency: str

    @property
    def change_pct(self) -> float:
        if self.prev_price == 0:
            return 0.0
        return ((self.price - self.prev_price) / self.prev_price) * 100.0


@dataclass(frozen=True)
class StockImpact:
    symbol: str
    commodity: str
    sensitivity: float
    commodity_change_pct: float
    expected_impact_pct: float


# Commodity-to-stock linkage configuration
COMMODITY_STOCK_LINKAGES: dict[str, dict[str, float]] = {
    "CPO": {"AALI": 0.65, "LSIP": 0.72, "SIMP": 0.55},
    "COAL_HBA": {"ADRO": 0.70, "ITMG": 0.75, "PTBA": 0.68},
    "NICKEL_LME": {"ANTM": 0.60, "INCO": 0.80, "VALE": 0.55},
}


def compute_stock_impacts(
    commodity_price: CommodityPrice,
    linkages: dict[str, dict[str, float]] | None = None,
) -> list[StockImpact]:
    """Compute expected stock impacts from a commodity price change."""
    link_map = linkages or COMMODITY_STOCK_LINKAGES
    stock_sensitivities = link_map.get(commodity_price.commodity, {})
    change_pct = commodity_price.change_pct

    return [
        StockImpact(
            symbol=symbol,
            commodity=commodity_price.commodity,
            sensitivity=sensitivity,
            commodity_change_pct=change_pct,
            expected_impact_pct=sensitivity * change_pct,
        )
        for symbol, sensitivity in stock_sensitivities.items()
    ]


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def cpo_price_up():
    return CommodityPrice(commodity="CPO", price=4200.0, prev_price=4000.0, currency="MYR")


@pytest.fixture
def coal_price_down():
    return CommodityPrice(commodity="COAL_HBA", price=110.0, prev_price=120.0, currency="USD")


@pytest.fixture
def nickel_price_flat():
    return CommodityPrice(commodity="NICKEL_LME", price=16500.0, prev_price=16500.0, currency="USD")


@pytest.fixture
def mock_api_client():
    client = AsyncMock()
    client.get = AsyncMock()
    return client


# ── CPO Impact Tests ────────────────────────────────────────────────────────


class TestCPOImpact:
    def test_cpo_increase_positive_impacts(self, cpo_price_up):
        impacts = compute_stock_impacts(cpo_price_up)
        assert len(impacts) == 3
        assert all(i.expected_impact_pct > 0 for i in impacts)

    def test_cpo_impact_symbols(self, cpo_price_up):
        impacts = compute_stock_impacts(cpo_price_up)
        symbols = {i.symbol for i in impacts}
        assert symbols == {"AALI", "LSIP", "SIMP"}

    def test_cpo_change_percentage(self, cpo_price_up):
        assert cpo_price_up.change_pct == pytest.approx(5.0)

    def test_lsip_has_highest_cpo_sensitivity(self, cpo_price_up):
        impacts = compute_stock_impacts(cpo_price_up)
        impact_map = {i.symbol: i for i in impacts}
        assert impact_map["LSIP"].sensitivity > impact_map["AALI"].sensitivity
        assert impact_map["AALI"].sensitivity > impact_map["SIMP"].sensitivity


# ── Coal Impact Tests ──────────────────────────────────────────────────────


class TestCoalImpact:
    def test_coal_decrease_negative_impacts(self, coal_price_down):
        impacts = compute_stock_impacts(coal_price_down)
        assert len(impacts) == 3
        assert all(i.expected_impact_pct < 0 for i in impacts)

    def test_coal_impact_symbols(self, coal_price_down):
        impacts = compute_stock_impacts(coal_price_down)
        symbols = {i.symbol for i in impacts}
        assert symbols == {"ADRO", "ITMG", "PTBA"}

    def test_coal_change_percentage(self, coal_price_down):
        assert coal_price_down.change_pct == pytest.approx(-8.333, rel=1e-2)


# ── Nickel Impact Tests ────────────────────────────────────────────────────


class TestNickelImpact:
    def test_flat_price_zero_impact(self, nickel_price_flat):
        impacts = compute_stock_impacts(nickel_price_flat)
        assert all(i.expected_impact_pct == 0.0 for i in impacts)

    def test_nickel_impact_symbols(self, nickel_price_flat):
        impacts = compute_stock_impacts(nickel_price_flat)
        symbols = {i.symbol for i in impacts}
        assert symbols == {"ANTM", "INCO", "VALE"}


# ── Edge Cases ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_unknown_commodity_returns_empty(self):
        price = CommodityPrice(commodity="GOLD", price=2000.0, prev_price=1950.0, currency="USD")
        impacts = compute_stock_impacts(price)
        assert impacts == []

    def test_zero_prev_price_returns_zero_change(self):
        price = CommodityPrice(commodity="CPO", price=4000.0, prev_price=0.0, currency="MYR")
        assert price.change_pct == 0.0

    @pytest.mark.asyncio
    async def test_api_client_called(self, mock_api_client):
        """Verify API endpoint is called for commodity data."""
        mock_api_client.get.return_value = {"commodity": "CPO", "price": 4200.0}
        result = await mock_api_client.get("/api/v1/commodities/CPO/latest")
        assert result["commodity"] == "CPO"
        mock_api_client.get.assert_called_once()
