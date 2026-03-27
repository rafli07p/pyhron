"""El Nino / La Nina (ENSO) impact on CPO production forecast.

Models the relationship between ENSO indices (ONI, SOI, Nino3.4) and
Indonesian palm oil production.  El Nino events reduce rainfall in
Sumatra and Kalimantan, depressing FFB (Fresh Fruit Bunch) yields
with a 6-12 month lag.

Key relationships:
  - El Nino → reduced rainfall → lower FFB yields → lower CPO output.
  - La Nina → increased rainfall → mixed impact (flooding risk vs moisture).
  - Neutral → baseline production assumptions apply.

Usage::

    forecaster = ENSOCPOProductionForecast()
    forecast = forecaster.forecast_production_impact(oni_value=-1.5)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class ENSOPhase(StrEnum):
    """ENSO phase classification based on ONI threshold."""

    STRONG_EL_NINO = "STRONG_EL_NINO"
    MODERATE_EL_NINO = "MODERATE_EL_NINO"
    WEAK_EL_NINO = "WEAK_EL_NINO"
    NEUTRAL = "NEUTRAL"
    WEAK_LA_NINA = "WEAK_LA_NINA"
    MODERATE_LA_NINA = "MODERATE_LA_NINA"
    STRONG_LA_NINA = "STRONG_LA_NINA"


@dataclass(frozen=True)
class CPOProductionForecast:
    """CPO production forecast based on ENSO conditions.

    Attributes:
        enso_phase: Classified ENSO phase.
        oni_value: Oceanic Nino Index value.
        production_impact_pct: Expected production change (%).
        yield_impact_kg_per_ha: FFB yield impact in kg/ha.
        affected_regions: Regions most affected.
        lag_months: Expected lag before impact materialises.
        confidence: Forecast confidence level.
        cpo_price_impact_pct: Expected CPO price impact (%).
    """

    enso_phase: ENSOPhase
    oni_value: float
    production_impact_pct: float
    yield_impact_kg_per_ha: float
    affected_regions: list[str]
    lag_months: int
    confidence: str
    cpo_price_impact_pct: float


# ENSO impact parameters
_BASELINE_YIELD_KG_PER_HA: float = 18_000.0
_INDONESIA_CPO_PRODUCTION_MT: float = 46.0  # million metric tons

_ENSO_YIELD_SENSITIVITY: dict[ENSOPhase, float] = {
    ENSOPhase.STRONG_EL_NINO: -0.15,
    ENSOPhase.MODERATE_EL_NINO: -0.08,
    ENSOPhase.WEAK_EL_NINO: -0.03,
    ENSOPhase.NEUTRAL: 0.0,
    ENSOPhase.WEAK_LA_NINA: 0.02,
    ENSOPhase.MODERATE_LA_NINA: 0.01,
    ENSOPhase.STRONG_LA_NINA: -0.03,  # Flooding risk
}


class ENSOCPOProductionForecast:
    """Forecast CPO production impact from ENSO conditions.

    Uses historical ONI-to-yield regression calibrated on Indonesian
    palm oil production data from 2000-2023.

    Args:
        baseline_yield: Baseline FFB yield in kg/ha.
        total_production_mt: Indonesia total CPO production in million MT.
    """

    def __init__(
        self,
        baseline_yield: float = _BASELINE_YIELD_KG_PER_HA,
        total_production_mt: float = _INDONESIA_CPO_PRODUCTION_MT,
    ) -> None:
        self._baseline_yield = baseline_yield
        self._total_production = total_production_mt

    def classify_enso_phase(self, oni_value: float) -> ENSOPhase:
        """Classify ENSO phase from Oceanic Nino Index value.

        Args:
            oni_value: ONI value (positive = El Nino, negative = La Nina).

        Returns:
            Classified ENSOPhase.
        """
        if oni_value >= 1.5:
            return ENSOPhase.STRONG_EL_NINO
        if oni_value >= 1.0:
            return ENSOPhase.MODERATE_EL_NINO
        if oni_value >= 0.5:
            return ENSOPhase.WEAK_EL_NINO
        if oni_value > -0.5:
            return ENSOPhase.NEUTRAL
        if oni_value > -1.0:
            return ENSOPhase.WEAK_LA_NINA
        if oni_value > -1.5:
            return ENSOPhase.MODERATE_LA_NINA
        return ENSOPhase.STRONG_LA_NINA

    def forecast_production_impact(self, oni_value: float) -> CPOProductionForecast:
        """Forecast CPO production impact given current ONI reading.

        Args:
            oni_value: Current Oceanic Nino Index value.

        Returns:
            CPOProductionForecast with expected production and price impacts.
        """
        phase = self.classify_enso_phase(oni_value)
        yield_sensitivity = _ENSO_YIELD_SENSITIVITY[phase]

        production_impact_pct = yield_sensitivity * 100.0
        yield_impact = self._baseline_yield * yield_sensitivity

        # CPO price elasticity: ~0.3 (inelastic supply).
        price_impact_pct = -production_impact_pct * 0.3

        affected_regions = self._get_affected_regions(phase)
        lag = 9 if oni_value > 0 else 6
        confidence = "HIGH" if abs(oni_value) >= 1.5 else "MEDIUM" if abs(oni_value) >= 0.5 else "LOW"

        forecast = CPOProductionForecast(
            enso_phase=phase,
            oni_value=oni_value,
            production_impact_pct=round(production_impact_pct, 2),
            yield_impact_kg_per_ha=round(yield_impact, 0),
            affected_regions=affected_regions,
            lag_months=lag,
            confidence=confidence,
            cpo_price_impact_pct=round(price_impact_pct, 2),
        )

        logger.info(
            "enso_cpo_forecast_generated",
            phase=phase.value,
            production_impact_pct=forecast.production_impact_pct,
            price_impact_pct=forecast.cpo_price_impact_pct,
        )
        return forecast

    @staticmethod
    def _get_affected_regions(phase: ENSOPhase) -> list[str]:
        """Determine most affected plantation regions by ENSO phase."""
        if phase in (ENSOPhase.STRONG_EL_NINO, ENSOPhase.MODERATE_EL_NINO):
            return ["South Sumatra", "Riau", "Central Kalimantan", "South Kalimantan"]
        if phase in (ENSOPhase.STRONG_LA_NINA, ENSOPhase.MODERATE_LA_NINA):
            return ["Central Kalimantan", "South Kalimantan"]  # Flood-prone
        return ["All regions (baseline)"]
