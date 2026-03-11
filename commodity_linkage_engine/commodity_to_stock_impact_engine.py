"""Core commodity-to-stock impact engine.

Translates commodity price movements into per-stock earnings impact
estimates for the most exposed Indonesian listed equities.

Commodity coverage:
  - CPO  → plantation stocks  (AALI, LSIP, SIMP, TBLA, BWPT, SSMS, PALM)
  - Coal → coal miners        (ADRO, PTBA, ITMG, BUMI, HRUM)
  - Nickel → nickel producers (INCO, ANTM, MDKA)
  - ICP Crude → energy stocks (PGAS, MEDC, ENRG)

Each method returns a list of :class:`StockEarningsImpactEstimate`
dataclasses with revenue, net-income, and EPS impact projections.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from commodity_linkage_engine.commodity_sensitivity_models.coal_price_miner_revenue_model import (
    CoalPriceMinerRevenueModel,
)
from commodity_linkage_engine.commodity_sensitivity_models.cpo_plantation_stock_sensitivity import (
    CPOPlantationStockSensitivity,
)
from commodity_linkage_engine.commodity_sensitivity_models.icp_energy_stock_sensitivity import (
    ICPEnergyStockSensitivity,
)
from commodity_linkage_engine.commodity_sensitivity_models.nickel_price_miner_revenue_model import (
    NickelPriceMinerRevenueModel,
)
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

logger = get_logger(__name__)


# ── Data Contracts ──────────────────────────────────────────────────────────


class CommodityType(enum.Enum):
    """Supported commodity types."""

    CPO = "CPO"
    COAL = "COAL"
    NICKEL = "NICKEL"
    ICP_CRUDE = "ICP_CRUDE"


class ConfidenceLevel(enum.Enum):
    """Confidence tier for an impact estimate."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class CommodityPriceChangeEvent:
    """Describes a commodity price movement.

    Attributes:
        commodity: Which commodity moved.
        change_pct: Percentage change (e.g. 10.0 = +10 %).
        change_absolute: Absolute change in commodity-native units
            (USD/ton for coal/nickel, MYR/ton for CPO, USD/bbl for ICP).
        source: Data source identifier (e.g. ``"reuters"``, ``"bisinfocus"``).
        timestamp_utc: ISO-8601 timestamp of the observation.
    """

    commodity: CommodityType
    change_pct: float
    change_absolute: float
    source: str
    timestamp_utc: str


@dataclass
class StockEarningsImpactEstimate:
    """Per-stock earnings impact estimate from a commodity price change.

    Attributes:
        ticker: IDX ticker (e.g. ``"AALI"``).
        commodity: The commodity driving the impact.
        revenue_impact_idr: Estimated revenue impact in IDR.
        net_income_impact_idr: Estimated net-income impact in IDR.
        eps_impact: Estimated EPS impact in IDR/share.
        impact_pct_of_revenue: Impact as a percentage of trailing revenue.
        confidence: Confidence tier.
        methodology: Human-readable description of the model.
        assumptions: Key assumptions underlying the estimate.
    """

    ticker: str
    commodity: CommodityType
    revenue_impact_idr: float
    net_income_impact_idr: float
    eps_impact: float
    impact_pct_of_revenue: float
    confidence: ConfidenceLevel
    methodology: str
    assumptions: list[str] = field(default_factory=list)


# ── Engine ──────────────────────────────────────────────────────────────────


class CommodityToStockImpactEngine:
    """Fan-out commodity price changes to per-stock earnings impacts.

    This is the top-level orchestrator that delegates to the individual
    commodity sensitivity models and returns a unified list of impact
    estimates.

    Args:
        usd_idr_rate: Assumed USD/IDR exchange rate for conversions.
    """

    def __init__(self, usd_idr_rate: float = 15_500.0) -> None:
        self._usd_idr = usd_idr_rate
        self._cpo_model = CPOPlantationStockSensitivity(usd_idr_rate=usd_idr_rate)
        self._coal_model = CoalPriceMinerRevenueModel(usd_idr_rate=usd_idr_rate)
        self._nickel_model = NickelPriceMinerRevenueModel(usd_idr_rate=usd_idr_rate)
        self._icp_model = ICPEnergyStockSensitivity(usd_idr_rate=usd_idr_rate)

    # ── CPO ─────────────────────────────────────────────────────────────

    def estimate_cpo_price_impact(self, cpo_price_change_pct: float) -> list[StockEarningsImpactEstimate]:
        """Estimate plantation stock earnings impact from CPO price change.

        Model: plantation_area * yield * OER * price_change, adjusted for
        hedging ratio, Domestic Market Obligation (DMO), and export tax/levy.

        Affected tickers: AALI, LSIP, SIMP, TBLA, BWPT, SSMS, PALM.

        Args:
            cpo_price_change_pct: CPO price change in percent
                (e.g. ``10.0`` → +10 %).

        Returns:
            Per-stock earnings impact estimates.
        """
        logger.info(
            "cpo_impact_estimation_start",
            cpo_price_change_pct=cpo_price_change_pct,
        )
        estimates = self._cpo_model.compute_all_impacts(cpo_price_change_pct)
        logger.info(
            "cpo_impact_estimation_complete",
            num_stocks=len(estimates),
        )
        return estimates

    # ── Coal ────────────────────────────────────────────────────────────

    def estimate_coal_price_impact(self, hba_change_usd_per_ton: float) -> list[StockEarningsImpactEstimate]:
        """Estimate coal miner earnings impact from HBA price change.

        Model: production_vol * (hba_change * (1 - royalty_rate)).
        DMO obligation: 25 % of production at USD 90/ton cap.

        Affected tickers: ADRO, PTBA, ITMG, BUMI, HRUM.

        Args:
            hba_change_usd_per_ton: HBA price change in USD/ton.

        Returns:
            Per-stock earnings impact estimates.
        """
        logger.info(
            "coal_impact_estimation_start",
            hba_change_usd_per_ton=hba_change_usd_per_ton,
        )
        estimates = self._coal_model.compute_all_impacts(hba_change_usd_per_ton)
        logger.info(
            "coal_impact_estimation_complete",
            num_stocks=len(estimates),
        )
        return estimates

    # ── Nickel ──────────────────────────────────────────────────────────

    def estimate_nickel_price_impact(self, lme_change_usd_per_ton: float) -> list[StockEarningsImpactEstimate]:
        """Estimate nickel producer earnings impact from LME nickel change.

        INCO has high correlation (matte product), ANTM partial
        (ferronickel), MDKA growing exposure.

        Args:
            lme_change_usd_per_ton: LME nickel price change in USD/ton.

        Returns:
            Per-stock earnings impact estimates.
        """
        logger.info(
            "nickel_impact_estimation_start",
            lme_change_usd_per_ton=lme_change_usd_per_ton,
        )
        estimates = self._nickel_model.compute_all_impacts(lme_change_usd_per_ton)
        logger.info(
            "nickel_impact_estimation_complete",
            num_stocks=len(estimates),
        )
        return estimates

    # ── ICP Crude ───────────────────────────────────────────────────────

    def estimate_icp_crude_impact(self, icp_change_usd_per_barrel: float) -> list[StockEarningsImpactEstimate]:
        """Estimate energy stock earnings impact from ICP crude change.

        Affected: PGAS, MEDC, ENRG.  Secondary impact on APBN subsidy
        burden is noted in assumptions but not modelled as an equity
        impact here.

        Args:
            icp_change_usd_per_barrel: ICP price change in USD/barrel.

        Returns:
            Per-stock earnings impact estimates.
        """
        logger.info(
            "icp_impact_estimation_start",
            icp_change_usd_per_barrel=icp_change_usd_per_barrel,
        )
        estimates = self._icp_model.compute_all_impacts(icp_change_usd_per_barrel)
        logger.info(
            "icp_impact_estimation_complete",
            num_stocks=len(estimates),
        )
        return estimates

    # ── Unified ─────────────────────────────────────────────────────────

    def estimate_impact(self, event: CommodityPriceChangeEvent) -> list[StockEarningsImpactEstimate]:
        """Dispatch a :class:`CommodityPriceChangeEvent` to the right model.

        Args:
            event: Commodity price change event.

        Returns:
            Per-stock earnings impact estimates.

        Raises:
            ValueError: If the commodity type is unsupported.
        """
        dispatch: dict[CommodityType, Callable[[], list[StockEarningsImpactEstimate]]] = {
            CommodityType.CPO: lambda: self.estimate_cpo_price_impact(event.change_pct),
            CommodityType.COAL: lambda: self.estimate_coal_price_impact(event.change_absolute),
            CommodityType.NICKEL: lambda: self.estimate_nickel_price_impact(event.change_absolute),
            CommodityType.ICP_CRUDE: lambda: self.estimate_icp_crude_impact(event.change_absolute),
        }
        handler = dispatch.get(event.commodity)
        if handler is None:
            raise ValueError(f"Unsupported commodity: {event.commodity}")
        return handler()

    def estimate_multi_commodity_impact(
        self, events: Sequence[CommodityPriceChangeEvent]
    ) -> list[StockEarningsImpactEstimate]:
        """Batch-estimate impacts for multiple commodity events.

        Args:
            events: Sequence of commodity price change events.

        Returns:
            Flat list of per-stock earnings impact estimates.
        """
        all_estimates: list[StockEarningsImpactEstimate] = []
        for event in events:
            all_estimates.extend(self.estimate_impact(event))
        return all_estimates
