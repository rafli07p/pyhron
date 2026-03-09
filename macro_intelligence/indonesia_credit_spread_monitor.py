"""Indonesian corporate vs government bond credit spread monitor.

Tracks credit spreads between Indonesian corporate bonds and
government benchmarks (SUN/SBN) across rating categories to
identify credit stress, sector-specific risk, and relative
value opportunities.

Rating scale (Pefindo): idAAA, idAA+, idAA, ..., idD.

Usage::

    monitor = IndonesiaCreditSpreadMonitor()
    spreads = monitor.compute_spreads(corporate_yields, govt_curve)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class CorporateBondYield:
    """Corporate bond yield observation.

    Attributes:
        issuer: Company name.
        ticker: IDX ticker of the issuer (if listed).
        bond_code: Bond series code.
        rating: Pefindo rating (e.g. ``idAAA``, ``idAA+``).
        tenor_years: Remaining maturity in years.
        yield_pct: Yield to maturity in percent.
        sector: Industry sector.
        observed_at: Observation timestamp.
    """

    issuer: str
    ticker: str | None
    bond_code: str
    rating: str
    tenor_years: float
    yield_pct: float
    sector: str
    observed_at: datetime


@dataclass
class CreditSpreadReading:
    """Credit spread reading for a single bond vs government benchmark.

    Attributes:
        bond_code: Corporate bond series code.
        issuer: Issuer name.
        ticker: IDX ticker if listed.
        rating: Pefindo rating.
        tenor_years: Bond maturity in years.
        corporate_yield: Corporate bond yield.
        benchmark_yield: Government benchmark yield at same tenor.
        spread_bps: Credit spread in basis points.
        z_score: Spread z-score vs 1-year historical mean.
        signal: ``WIDE`` (stressed), ``TIGHT`` (rich), ``NORMAL``.
    """

    bond_code: str
    issuer: str
    ticker: str | None
    rating: str
    tenor_years: float
    corporate_yield: float
    benchmark_yield: float
    spread_bps: float
    z_score: float
    signal: str


@dataclass
class CreditSpreadDashboard:
    """Aggregated credit spread dashboard.

    Attributes:
        generated_at: Dashboard generation timestamp.
        readings: Per-bond credit spread readings.
        avg_spread_by_rating: Average spread by rating category.
        avg_spread_by_sector: Average spread by sector.
        stress_indicator: Overall credit stress level.
    """

    generated_at: datetime
    readings: list[CreditSpreadReading]
    avg_spread_by_rating: dict[str, float]
    avg_spread_by_sector: dict[str, float]
    stress_indicator: str


# ── Historical average spreads for z-score calculation ──────────────────────

_HISTORICAL_SPREADS_BPS: dict[str, tuple[float, float]] = {
    "idAAA": (80.0, 25.0),
    "idAA+": (120.0, 35.0),
    "idAA": (150.0, 40.0),
    "idAA-": (180.0, 50.0),
    "idA+": (220.0, 60.0),
    "idA": (280.0, 75.0),
    "idA-": (350.0, 90.0),
    "idBBB+": (450.0, 120.0),
    "idBBB": (550.0, 150.0),
}


class IndonesiaCreditSpreadMonitor:
    """Monitor corporate-government bond credit spreads.

    Computes spreads, z-scores, and stress indicators across
    the Indonesian corporate bond market segmented by rating
    and sector.

    Args:
        stress_z_threshold: Z-score above which spread is ``WIDE``.
        rich_z_threshold: Z-score below which spread is ``TIGHT``.
    """

    def __init__(
        self,
        stress_z_threshold: float = 1.5,
        rich_z_threshold: float = -1.5,
    ) -> None:
        self._stress_z = stress_z_threshold
        self._rich_z = rich_z_threshold

        logger.info(
            "credit_spread_monitor_initialised",
            stress_z=stress_z_threshold,
            rich_z=rich_z_threshold,
        )

    def compute_spreads(
        self,
        corporate_yields: list[CorporateBondYield],
        govt_yield_interpolator: Any,
    ) -> CreditSpreadDashboard:
        """Compute credit spreads for all corporate bonds.

        Args:
            corporate_yields: List of corporate bond yield observations.
            govt_yield_interpolator: Callable(tenor) -> govt yield in pct.

        Returns:
            CreditSpreadDashboard with readings and aggregations.
        """
        readings: list[CreditSpreadReading] = []

        for bond in corporate_yields:
            benchmark = govt_yield_interpolator(bond.tenor_years)
            spread_bps = (bond.yield_pct - benchmark) * 100

            hist = _HISTORICAL_SPREADS_BPS.get(bond.rating, (200.0, 80.0))
            z_score = (spread_bps - hist[0]) / hist[1] if hist[1] > 0 else 0.0

            if z_score >= self._stress_z:
                signal = "WIDE"
            elif z_score <= self._rich_z:
                signal = "TIGHT"
            else:
                signal = "NORMAL"

            readings.append(
                CreditSpreadReading(
                    bond_code=bond.bond_code,
                    issuer=bond.issuer,
                    ticker=bond.ticker,
                    rating=bond.rating,
                    tenor_years=bond.tenor_years,
                    corporate_yield=bond.yield_pct,
                    benchmark_yield=round(benchmark, 4),
                    spread_bps=round(spread_bps, 2),
                    z_score=round(z_score, 4),
                    signal=signal,
                )
            )

        avg_by_rating = self._aggregate_by(readings, key="rating")
        avg_by_sector = self._aggregate_by_sector(readings, corporate_yields)

        wide_count = sum(1 for r in readings if r.signal == "WIDE")
        if wide_count > len(readings) * 0.3:
            stress = "ELEVATED"
        elif wide_count > 0:
            stress = "MODERATE"
        else:
            stress = "LOW"

        dashboard = CreditSpreadDashboard(
            generated_at=datetime.now(UTC),
            readings=readings,
            avg_spread_by_rating=avg_by_rating,
            avg_spread_by_sector=avg_by_sector,
            stress_indicator=stress,
        )

        logger.info(
            "credit_spreads_computed",
            num_bonds=len(readings),
            stress=stress,
            wide_count=wide_count,
        )
        return dashboard

    @staticmethod
    def _aggregate_by(readings: list[CreditSpreadReading], key: str) -> dict[str, float]:
        """Compute average spread by a grouping key."""
        groups: dict[str, list[float]] = {}
        for r in readings:
            k = getattr(r, key)
            groups.setdefault(k, []).append(r.spread_bps)
        return {k: round(sum(v) / len(v), 2) for k, v in groups.items()}

    @staticmethod
    def _aggregate_by_sector(
        readings: list[CreditSpreadReading],
        bonds: list[CorporateBondYield],
    ) -> dict[str, float]:
        """Compute average spread by sector."""
        sector_map = {b.bond_code: b.sector for b in bonds}
        groups: dict[str, list[float]] = {}
        for r in readings:
            sector = sector_map.get(r.bond_code, "Other")
            groups.setdefault(sector, []).append(r.spread_bps)
        return {k: round(sum(v) / len(v), 2) for k, v in groups.items()}
