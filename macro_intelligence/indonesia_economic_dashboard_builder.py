"""Aggregate Indonesian macroeconomic dashboard builder.

Consolidates key macro indicators into a unified dashboard for
investment decision support: GDP growth, inflation (CPI/PPI),
trade balance, FX reserves, current account, BI rate, and
credit growth.

Data sources:
  - Bank Indonesia (BI): monetary policy, FX reserves, credit data.
  - BPS (Badan Pusat Statistik): GDP, inflation, trade balance.
  - Ministry of Finance: fiscal data.

Usage::

    builder = IndonesiaEconomicDashboardBuilder()
    dashboard = await builder.build_dashboard()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass
class MacroIndicator:
    """Single macroeconomic indicator reading.

    Attributes:
        name: Indicator name.
        value: Current value.
        unit: Unit of measurement.
        period: Reporting period (e.g. ``2025-Q4``).
        previous_value: Prior period value.
        yoy_change: Year-over-year change.
        source: Data source.
        updated_at: Last update timestamp.
    """

    name: str
    value: float
    unit: str
    period: str
    previous_value: float | None = None
    yoy_change: float | None = None
    source: str = "BPS"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EconomicDashboard:
    """Aggregated macroeconomic dashboard.

    Attributes:
        generated_at: Dashboard generation timestamp.
        indicators: Dictionary of indicator name to reading.
        summary_score: Composite macro health score (-1 to +1).
        regime: Macro regime classification.
        risks: Key risk factors identified.
    """

    generated_at: datetime
    indicators: dict[str, MacroIndicator]
    summary_score: float
    regime: str
    risks: list[str] = field(default_factory=list)


class IndonesiaEconomicDashboardBuilder:
    """Build aggregate Indonesian macroeconomic dashboard.

    Collects latest readings for each indicator and computes a
    composite macro health score using z-score normalisation of
    each indicator against its historical distribution.

    Args:
        indicator_weights: Custom weights for composite score.
    """

    _DEFAULT_WEIGHTS: dict[str, float] = {
        "gdp_growth": 0.20,
        "inflation_cpi": -0.15,
        "bi_rate": -0.10,
        "trade_balance": 0.15,
        "fx_reserves": 0.10,
        "credit_growth": 0.10,
        "current_account": 0.10,
        "pmi_manufacturing": 0.10,
    }

    def __init__(
        self, indicator_weights: dict[str, float] | None = None
    ) -> None:
        self._weights = indicator_weights or dict(self._DEFAULT_WEIGHTS)
        logger.info(
            "dashboard_builder_initialised",
            num_indicators=len(self._weights),
        )

    async def build_dashboard(
        self, indicators: dict[str, MacroIndicator] | None = None
    ) -> EconomicDashboard:
        """Build the macroeconomic dashboard from latest indicators.

        Args:
            indicators: Pre-fetched indicator readings. If None, uses
                placeholder values for demonstration.

        Returns:
            EconomicDashboard with composite score and regime classification.
        """
        if indicators is None:
            indicators = self._get_placeholder_indicators()

        score = self._compute_composite_score(indicators)
        regime = self._classify_regime(score)
        risks = self._identify_risks(indicators)

        dashboard = EconomicDashboard(
            generated_at=datetime.now(timezone.utc),
            indicators=indicators,
            summary_score=round(score, 4),
            regime=regime,
            risks=risks,
        )

        logger.info(
            "dashboard_built",
            score=dashboard.summary_score,
            regime=regime,
            num_risks=len(risks),
        )
        return dashboard

    def _compute_composite_score(
        self, indicators: dict[str, MacroIndicator]
    ) -> float:
        """Compute weighted composite macro health score.

        Normalises each indicator against reference values and applies
        directional weights (negative weight = higher is worse).

        Args:
            indicators: Current indicator readings.

        Returns:
            Composite score in [-1, 1] range.
        """
        _REFERENCE: dict[str, tuple[float, float]] = {
            "gdp_growth": (5.0, 1.0),
            "inflation_cpi": (3.0, 1.5),
            "bi_rate": (6.0, 1.0),
            "trade_balance": (3.0, 5.0),
            "fx_reserves": (140.0, 20.0),
            "credit_growth": (10.0, 3.0),
            "current_account": (-1.5, 1.0),
            "pmi_manufacturing": (52.0, 3.0),
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for name, weight in self._weights.items():
            if name not in indicators or name not in _REFERENCE:
                continue
            mean, std = _REFERENCE[name]
            z = (indicators[name].value - mean) / std if std > 0 else 0.0
            weighted_sum += weight * z
            total_weight += abs(weight)

        if total_weight == 0:
            return 0.0
        raw = weighted_sum / total_weight
        return max(-1.0, min(1.0, raw))

    @staticmethod
    def _classify_regime(score: float) -> str:
        """Classify macro regime from composite score."""
        if score >= 0.3:
            return "EXPANSIONARY"
        elif score >= -0.3:
            return "NEUTRAL"
        return "CONTRACTIONARY"

    @staticmethod
    def _identify_risks(indicators: dict[str, MacroIndicator]) -> list[str]:
        """Identify key macro risk factors from indicator readings."""
        risks: list[str] = []
        cpi = indicators.get("inflation_cpi")
        if cpi and cpi.value > 5.0:
            risks.append(f"Elevated inflation: {cpi.value}% exceeds BI target")
        ca = indicators.get("current_account")
        if ca and ca.value < -3.0:
            risks.append(f"Wide current account deficit: {ca.value}% of GDP")
        fx = indicators.get("fx_reserves")
        if fx and fx.value < 100.0:
            risks.append(f"Low FX reserves: USD {fx.value}B (< 6 months imports)")
        return risks

    @staticmethod
    def _get_placeholder_indicators() -> dict[str, MacroIndicator]:
        """Return placeholder indicator values for demonstration."""
        return {
            "gdp_growth": MacroIndicator("GDP Growth", 5.05, "% YoY", "2025-Q3", 5.11),
            "inflation_cpi": MacroIndicator("CPI Inflation", 2.84, "% YoY", "2025-10", 2.28),
            "bi_rate": MacroIndicator("BI 7-Day RR Rate", 6.00, "%", "2025-10", 6.25),
            "trade_balance": MacroIndicator("Trade Balance", 3.56, "USD Billion", "2025-10", 3.46),
            "fx_reserves": MacroIndicator("FX Reserves", 149.9, "USD Billion", "2025-10", 150.2),
            "credit_growth": MacroIndicator("Credit Growth", 10.4, "% YoY", "2025-09", 10.7),
            "current_account": MacroIndicator("Current Account", -0.8, "% GDP", "2025-Q3", -0.5),
            "pmi_manufacturing": MacroIndicator("PMI Manufacturing", 51.9, "Index", "2025-10", 52.3),
        }
