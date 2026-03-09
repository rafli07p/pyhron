"""Unit tests for CPO-to-plantation stock sensitivity model.

Tests that CPO price changes produce expected directional impacts on
Indonesian plantation stocks: AALI, LSIP, SIMP.

CPO (Crude Palm Oil) is the primary revenue driver for plantation companies.
When CPO price rises, revenue and margins expand, positively impacting stock price.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

# ── Sensitivity Model (pure functions under test) ───────────────────────────


@dataclass(frozen=True)
class CommodityImpact:
    """Impact of a commodity price change on a stock."""

    symbol: str
    commodity: str
    sensitivity: float  # beta: stock return per 1% commodity return
    impact_pct: float  # expected stock return for the given commodity move


# Historical beta estimates for CPO sensitivity (stylized)
CPO_SENSITIVITIES: dict[str, float] = {
    "AALI": 0.65,
    "LSIP": 0.72,
    "SIMP": 0.55,
}


def compute_cpo_impact(
    symbol: str,
    cpo_price_change_pct: float,
    sensitivities: dict[str, float] | None = None,
) -> CommodityImpact:
    """Compute expected stock impact from a CPO price change.

    Args:
        symbol: Plantation stock ticker.
        cpo_price_change_pct: CPO price change in percent (e.g. 5.0 for +5%).
        sensitivities: Override sensitivity map for testing.

    Returns:
        CommodityImpact with the estimated stock return.
    """
    sens_map = sensitivities or CPO_SENSITIVITIES
    sensitivity = sens_map.get(symbol, 0.0)
    impact = sensitivity * cpo_price_change_pct
    return CommodityImpact(
        symbol=symbol,
        commodity="CPO",
        sensitivity=sensitivity,
        impact_pct=impact,
    )


# ── Positive CPO Impact Tests ──────────────────────────────────────────────


class TestCPOPriceIncrease:
    """CPO price increases should produce positive impacts on plantation stocks."""

    @pytest.mark.parametrize("symbol", ["AALI", "LSIP", "SIMP"])
    def test_positive_cpo_gives_positive_impact(self, symbol):
        result = compute_cpo_impact(symbol, cpo_price_change_pct=5.0)
        assert result.impact_pct > 0
        assert result.commodity == "CPO"

    def test_aali_sensitivity_magnitude(self):
        result = compute_cpo_impact("AALI", cpo_price_change_pct=10.0)
        assert result.impact_pct == pytest.approx(6.5)  # 0.65 * 10

    def test_lsip_has_highest_sensitivity(self):
        aali = compute_cpo_impact("AALI", 10.0)
        lsip = compute_cpo_impact("LSIP", 10.0)
        simp = compute_cpo_impact("SIMP", 10.0)
        assert lsip.impact_pct > aali.impact_pct > simp.impact_pct


# ── Negative CPO Impact Tests ──────────────────────────────────────────────


class TestCPOPriceDecrease:
    """CPO price decreases should produce negative impacts."""

    @pytest.mark.parametrize("symbol", ["AALI", "LSIP", "SIMP"])
    def test_negative_cpo_gives_negative_impact(self, symbol):
        result = compute_cpo_impact(symbol, cpo_price_change_pct=-5.0)
        assert result.impact_pct < 0

    def test_symmetry_of_impact(self):
        up = compute_cpo_impact("AALI", 5.0)
        down = compute_cpo_impact("AALI", -5.0)
        assert up.impact_pct == pytest.approx(-down.impact_pct)


# ── Edge Cases ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_zero_change_gives_zero_impact(self):
        result = compute_cpo_impact("AALI", cpo_price_change_pct=0.0)
        assert result.impact_pct == 0.0

    def test_unknown_symbol_gives_zero_sensitivity(self):
        result = compute_cpo_impact("UNKNOWN", cpo_price_change_pct=10.0)
        assert result.sensitivity == 0.0
        assert result.impact_pct == 0.0

    def test_custom_sensitivity_override(self):
        custom = {"AALI": 0.80}
        result = compute_cpo_impact("AALI", 10.0, sensitivities=custom)
        assert result.impact_pct == pytest.approx(8.0)

    def test_impact_dataclass_is_frozen(self):
        result = compute_cpo_impact("AALI", 5.0)
        with pytest.raises(AttributeError):
            result.impact_pct = 999.0
