"""ICP crude oil → energy stock sensitivity model.

Models the impact of ICP (Indonesian Crude Price) changes on energy
companies listed on IDX.

# TODO: Move hardcoded company profiles and production data to database-backed
# or config-file-based reference data with quarterly update process.

ICP is the government reference price for Indonesian crude oil,
determined monthly by ESDM.  It affects:
  - Direct revenue for upstream producers (MEDC, ENRG).
  - Gas contract pricing for PGAS (many gas contracts have
    oil-price-linked formulas with slope and constant).
  - APBN fiscal balance (subsidy burden on BBM/LPG).

The APBN secondary impact is noted in assumptions but modelled
separately in macro_intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass

from commodity_linkage_engine.types import (
    CommodityType,
    ConfidenceLevel,
    StockEarningsImpactEstimate,
)
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class EnergyCompanyProfile:
    """Profile for an energy company.

    Attributes:
        ticker: IDX ticker symbol.
        oil_production_bopd: Oil production in barrels of oil per day.
        gas_production_boepd: Gas production in barrels of oil equivalent/day.
        oil_price_sensitivity: Fraction of revenue sensitive to ICP.
        gas_oil_price_linkage: Slope of gas price vs oil price formula
            (many Indonesian gas contracts: gas_price = slope * ICP + constant).
        cost_recovery_pct: PSC cost recovery percentage (reduces upside).
        government_take_pct: Government take under PSC gross-split.
        net_margin: Approximate net profit margin.
        shares_outstanding: Number of shares.
        trailing_revenue_idr: Trailing 12-month revenue in IDR.
    """

    ticker: str
    oil_production_bopd: float
    gas_production_boepd: float
    oil_price_sensitivity: float
    gas_oil_price_linkage: float
    cost_recovery_pct: float
    government_take_pct: float
    net_margin: float
    shares_outstanding: int
    trailing_revenue_idr: float


_ENERGY_COMPANIES: list[EnergyCompanyProfile] = [
    EnergyCompanyProfile(
        ticker="PGAS",
        oil_production_bopd=0,
        gas_production_boepd=85_000,
        oil_price_sensitivity=0.30,
        gas_oil_price_linkage=0.12,
        cost_recovery_pct=0.0,
        government_take_pct=0.0,
        net_margin=0.10,
        shares_outstanding=24_241_508_196,
        trailing_revenue_idr=42_000_000_000_000,
    ),
    EnergyCompanyProfile(
        ticker="MEDC",
        oil_production_bopd=45_000,
        gas_production_boepd=110_000,
        oil_price_sensitivity=0.85,
        gas_oil_price_linkage=0.11,
        cost_recovery_pct=0.35,
        government_take_pct=0.57,
        net_margin=0.18,
        shares_outstanding=21_258_270_000,
        trailing_revenue_idr=28_000_000_000_000,
    ),
    EnergyCompanyProfile(
        ticker="ENRG",
        oil_production_bopd=15_000,
        gas_production_boepd=30_000,
        oil_price_sensitivity=0.70,
        gas_oil_price_linkage=0.10,
        cost_recovery_pct=0.30,
        government_take_pct=0.60,
        net_margin=0.12,
        shares_outstanding=94_837_309_107,
        trailing_revenue_idr=8_500_000_000_000,
    ),
]

# Days per year for production annualization.
_DAYS_PER_YEAR: int = 365


class ICPEnergyStockSensitivity:
    """Model ICP crude price change → energy company revenue impact.

    For upstream producers under PSC (Production Sharing Contract):
        revenue_delta = (oil_bopd + gas_boepd * gas_linkage_slope)
                        * 365 * icp_change
                        * (1 - government_take)

    For PGAS (midstream gas distribution):
        revenue_delta = gas_boepd * 365 * icp_change * oil_sensitivity
        (gas contracts partially linked to oil price)

    Args:
        usd_idr_rate: USD/IDR exchange rate.
    """

    def __init__(self, usd_idr_rate: float = 15_500.0) -> None:
        self._usd_idr = usd_idr_rate

    def _compute_company_impact(
        self,
        company: EnergyCompanyProfile,
        icp_change_usd_per_barrel: float,
    ) -> StockEarningsImpactEstimate:
        """Compute earnings impact for a single energy company.

        Args:
            company: Energy company profile.
            icp_change_usd_per_barrel: ICP crude price change in USD/bbl.

        Returns:
            Earnings impact estimate.
        """
        # Oil revenue impact (direct ICP sensitivity).
        oil_revenue_delta_usd = (
            company.oil_production_bopd * _DAYS_PER_YEAR * icp_change_usd_per_barrel * company.oil_price_sensitivity
        )

        # Gas revenue impact (oil-price-linked gas contracts).
        # Gas price change = slope * ICP change.
        gas_price_change_usd_per_boe = company.gas_oil_price_linkage * icp_change_usd_per_barrel
        gas_revenue_delta_usd = company.gas_production_boepd * _DAYS_PER_YEAR * gas_price_change_usd_per_boe

        # Total gross revenue impact.
        gross_revenue_delta_usd = oil_revenue_delta_usd + gas_revenue_delta_usd

        # PSC government take reduces the company's net share.
        if company.government_take_pct > 0:
            net_revenue_delta_usd = gross_revenue_delta_usd * (1.0 - company.government_take_pct)
        else:
            net_revenue_delta_usd = gross_revenue_delta_usd

        revenue_impact_idr = net_revenue_delta_usd * self._usd_idr
        net_income_impact_idr = revenue_impact_idr * company.net_margin
        eps_impact = net_income_impact_idr / company.shares_outstanding

        impact_pct = (
            abs(revenue_impact_idr) / company.trailing_revenue_idr * 100.0 if company.trailing_revenue_idr > 0 else 0.0
        )

        # Upstream producers have higher confidence than midstream.
        if company.oil_production_bopd > 0 and company.oil_price_sensitivity >= 0.70:
            confidence = ConfidenceLevel.HIGH
        elif company.gas_oil_price_linkage > 0:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        return StockEarningsImpactEstimate(
            ticker=company.ticker,
            commodity=CommodityType.ICP_CRUDE,
            revenue_impact_idr=revenue_impact_idr,
            net_income_impact_idr=net_income_impact_idr,
            eps_impact=eps_impact,
            impact_pct_of_revenue=impact_pct,
            confidence=confidence,
            methodology=(
                "oil_bopd * icp_change * sensitivity + gas_boepd * (slope * icp_change) * 365 * (1 - gov_take)"
            ),
            assumptions=[
                f"Oil production: {company.oil_production_bopd:,.0f} BOPD",
                f"Gas production: {company.gas_production_boepd:,.0f} BOEPD",
                f"Oil price sensitivity: {company.oil_price_sensitivity:.0%}",
                f"Gas-oil linkage slope: {company.gas_oil_price_linkage}",
                f"Government take: {company.government_take_pct:.0%}",
                f"USD/IDR: {self._usd_idr:,.0f}",
                "Secondary APBN subsidy impact not modelled here",
            ],
        )

    def compute_all_impacts(self, icp_change_usd_per_barrel: float) -> list[StockEarningsImpactEstimate]:
        """Compute impact across all covered energy stocks.

        Args:
            icp_change_usd_per_barrel: ICP price change in USD/barrel.

        Returns:
            List of earnings impact estimates for all energy tickers.
        """
        estimates: list[StockEarningsImpactEstimate] = []
        for company in _ENERGY_COMPANIES:
            estimate = self._compute_company_impact(company, icp_change_usd_per_barrel)
            logger.info(
                "icp_company_impact_computed",
                ticker=company.ticker,
                revenue_impact_idr=estimate.revenue_impact_idr,
            )
            estimates.append(estimate)
        return estimates
