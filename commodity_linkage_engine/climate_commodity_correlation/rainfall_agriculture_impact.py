"""Rainfall impact on Indonesian agricultural commodity production.

Models the relationship between regional rainfall anomalies and
production of key Indonesian agricultural commodities: rice, sugar,
coffee, cocoa, and rubber.  Supports both deficit (drought) and
excess (flooding) scenarios.

Data sources:
  - BMKG (Badan Meteorologi, Klimatologi, dan Geofisika) rainfall data.
  - BPS (Badan Pusat Statistik) agricultural production statistics.

Usage::

    model = RainfallAgricultureImpact()
    impact = model.estimate_production_impact("rice", rainfall_anomaly_mm=-50)
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class CropProfile:
    """Agricultural crop sensitivity profile.

    Attributes:
        crop_name: Crop identifier.
        optimal_rainfall_mm: Monthly optimal rainfall in mm.
        deficit_sensitivity: Production drop per mm deficit below optimal.
        excess_sensitivity: Production drop per mm excess above threshold.
        excess_threshold_mm: Monthly rainfall above which flooding occurs.
        primary_regions: Major production regions.
        affected_tickers: IDX-listed stocks with exposure.
    """

    crop_name: str
    optimal_rainfall_mm: float
    deficit_sensitivity: float
    excess_sensitivity: float
    excess_threshold_mm: float
    primary_regions: list[str]
    affected_tickers: list[str]


@dataclass(frozen=True)
class RainfallImpactEstimate:
    """Production impact estimate from rainfall anomaly.

    Attributes:
        crop_name: Crop affected.
        rainfall_anomaly_mm: Departure from normal (negative = deficit).
        production_impact_pct: Expected production change (%).
        scenario: ``deficit``, ``excess``, or ``normal``.
        affected_regions: Regions most impacted.
        affected_tickers: IDX stocks with exposure.
        price_impact_pct: Expected commodity price impact (%).
        confidence: Estimate confidence level.
    """

    crop_name: str
    rainfall_anomaly_mm: float
    production_impact_pct: float
    scenario: str
    affected_regions: list[str]
    affected_tickers: list[str]
    price_impact_pct: float
    confidence: str


_CROP_PROFILES: dict[str, CropProfile] = {
    "rice": CropProfile(
        crop_name="rice",
        optimal_rainfall_mm=200,
        deficit_sensitivity=0.08,
        excess_sensitivity=0.05,
        excess_threshold_mm=350,
        primary_regions=["Java", "Sulawesi", "Sumatra"],
        affected_tickers=["AALI", "LSIP"],
    ),
    "sugar": CropProfile(
        crop_name="sugar",
        optimal_rainfall_mm=150,
        deficit_sensitivity=0.10,
        excess_sensitivity=0.06,
        excess_threshold_mm=300,
        primary_regions=["East Java", "Lampung"],
        affected_tickers=["SIMP"],
    ),
    "rubber": CropProfile(
        crop_name="rubber",
        optimal_rainfall_mm=200,
        deficit_sensitivity=0.06,
        excess_sensitivity=0.03,
        excess_threshold_mm=400,
        primary_regions=["South Sumatra", "North Sumatra", "Kalimantan"],
        affected_tickers=["AALI", "LSIP"],
    ),
    "coffee": CropProfile(
        crop_name="coffee",
        optimal_rainfall_mm=180,
        deficit_sensitivity=0.12,
        excess_sensitivity=0.04,
        excess_threshold_mm=350,
        primary_regions=["Lampung", "South Sumatra", "East Java"],
        affected_tickers=[],
    ),
    "cocoa": CropProfile(
        crop_name="cocoa",
        optimal_rainfall_mm=170,
        deficit_sensitivity=0.09,
        excess_sensitivity=0.05,
        excess_threshold_mm=320,
        primary_regions=["Sulawesi", "Sumatra"],
        affected_tickers=[],
    ),
}


class RainfallAgricultureImpact:
    """Model rainfall anomaly impact on agricultural production.

    Uses crop-specific sensitivity coefficients calibrated from
    historical BMKG rainfall data and BPS production statistics.
    """

    def __init__(self) -> None:
        self._profiles = dict(_CROP_PROFILES)
        logger.info(
            "rainfall_agriculture_model_initialised",
            num_crops=len(self._profiles),
        )

    def estimate_production_impact(self, crop: str, rainfall_anomaly_mm: float) -> RainfallImpactEstimate:
        """Estimate crop production impact from rainfall anomaly.

        Args:
            crop: Crop name (rice, sugar, rubber, coffee, cocoa).
            rainfall_anomaly_mm: Monthly rainfall departure from normal
                (negative = deficit, positive = excess).

        Returns:
            RainfallImpactEstimate with production and price impacts.

        Raises:
            ValueError: If crop is not in the supported profiles.
        """
        profile = self._profiles.get(crop)
        if profile is None:
            raise ValueError(f"Unsupported crop: {crop}. Supported: {list(self._profiles)}")

        anomaly = rainfall_anomaly_mm

        if anomaly < 0:
            scenario = "deficit"
            impact_pct = anomaly * profile.deficit_sensitivity
        elif anomaly > (profile.excess_threshold_mm - profile.optimal_rainfall_mm):
            scenario = "excess"
            excess = anomaly - (profile.excess_threshold_mm - profile.optimal_rainfall_mm)
            impact_pct = -abs(excess) * profile.excess_sensitivity
        else:
            scenario = "normal"
            impact_pct = 0.0

        # Price elasticity: supply shock → inverse price response.
        price_impact_pct = -impact_pct * 0.5

        confidence = "HIGH" if abs(anomaly) >= 100 else "MEDIUM" if abs(anomaly) >= 50 else "LOW"

        estimate = RainfallImpactEstimate(
            crop_name=crop,
            rainfall_anomaly_mm=rainfall_anomaly_mm,
            production_impact_pct=round(impact_pct, 2),
            scenario=scenario,
            affected_regions=profile.primary_regions,
            affected_tickers=profile.affected_tickers,
            price_impact_pct=round(price_impact_pct, 2),
            confidence=confidence,
        )

        logger.info(
            "rainfall_impact_estimated",
            crop=crop,
            scenario=scenario,
            production_impact_pct=estimate.production_impact_pct,
        )
        return estimate

    def estimate_all_crops(self, rainfall_anomaly_mm: float) -> list[RainfallImpactEstimate]:
        """Estimate impact across all supported crops.

        Args:
            rainfall_anomaly_mm: Monthly rainfall departure from normal.

        Returns:
            List of impact estimates for all crops.
        """
        return [self.estimate_production_impact(crop, rainfall_anomaly_mm) for crop in self._profiles]
