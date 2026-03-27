"""CPO plantation stock sensitivity model.

Detailed model mapping CPO price movements to revenue and earnings
impact for Indonesian listed plantation companies.

Profiles are loaded from the ``commodity_company_profiles`` database table
(see ``profile_loader.py``).  Hardcoded fallback data is retained for offline
development and tests only.

Revenue model per company:
    revenue_delta = plantation_area_ha * ffb_yield_ton_per_ha * oer
                    * cpo_price_change_per_ton * (1 - hedging_ratio)
                    * (1 - dmo_pct) * (1 - export_levy_effective_rate)

The model accounts for:
  - Company-specific plantation area, FFB yield, and OER.
  - Hedging ratios (larger companies hedge more).
  - DMO (Domestic Market Obligation) set by BPDPKS.
  - Progressive export levy structure introduced in 2022.
  - Downstream refining margins where applicable.
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


# Company Data
@dataclass(frozen=True)
class PlantationCompanyProfile:
    """Static profile for a plantation company.

    Attributes:
        ticker: IDX ticker symbol.
        plantation_area_ha: Total planted area in hectares.
        ffb_yield_ton_per_ha: Fresh fruit bunch yield (metric tons / ha / yr).
        oer_pct: Oil extraction rate (fraction, e.g. 0.22 = 22 %).
        hedging_ratio: Fraction of production forward-sold.
        net_margin: Approximate net profit margin.
        shares_outstanding: Number of shares for EPS calculation.
        trailing_revenue_idr: Trailing twelve month revenue in IDR.
        downstream_refining: Whether company has downstream refinery.
        dmo_allocation_pct: Fraction allocated to domestic market
            obligation at below-market price.
    """

    ticker: str
    plantation_area_ha: float
    ffb_yield_ton_per_ha: float
    oer_pct: float
    hedging_ratio: float
    net_margin: float
    shares_outstanding: int
    trailing_revenue_idr: float
    downstream_refining: bool = False
    dmo_allocation_pct: float = 0.20


# Fallback data for offline development/tests. Production reads from DB.
_PLANTATION_COMPANIES: list[PlantationCompanyProfile] = [
    PlantationCompanyProfile(
        ticker="AALI",
        plantation_area_ha=200_000,
        ffb_yield_ton_per_ha=24.0,
        oer_pct=0.22,
        hedging_ratio=0.15,
        net_margin=0.12,
        shares_outstanding=1_574_745_000,
        trailing_revenue_idr=21_500_000_000_000,
        downstream_refining=True,
        dmo_allocation_pct=0.20,
    ),
    PlantationCompanyProfile(
        ticker="LSIP",
        plantation_area_ha=95_000,
        ffb_yield_ton_per_ha=20.0,
        oer_pct=0.21,
        hedging_ratio=0.10,
        net_margin=0.18,
        shares_outstanding=6_822_864_000,
        trailing_revenue_idr=6_800_000_000_000,
        downstream_refining=False,
        dmo_allocation_pct=0.20,
    ),
    PlantationCompanyProfile(
        ticker="SIMP",
        plantation_area_ha=250_000,
        ffb_yield_ton_per_ha=19.0,
        oer_pct=0.21,
        hedging_ratio=0.20,
        net_margin=0.06,
        shares_outstanding=15_816_310_000,
        trailing_revenue_idr=16_200_000_000_000,
        downstream_refining=True,
        dmo_allocation_pct=0.25,
    ),
    PlantationCompanyProfile(
        ticker="TBLA",
        plantation_area_ha=42_000,
        ffb_yield_ton_per_ha=21.0,
        oer_pct=0.22,
        hedging_ratio=0.12,
        net_margin=0.08,
        shares_outstanding=5_340_000_000,
        trailing_revenue_idr=11_500_000_000_000,
        downstream_refining=True,
        dmo_allocation_pct=0.20,
    ),
    PlantationCompanyProfile(
        ticker="BWPT",
        plantation_area_ha=60_000,
        ffb_yield_ton_per_ha=16.0,
        oer_pct=0.20,
        hedging_ratio=0.05,
        net_margin=0.04,
        shares_outstanding=11_666_183_000,
        trailing_revenue_idr=3_400_000_000_000,
        downstream_refining=False,
        dmo_allocation_pct=0.20,
    ),
    PlantationCompanyProfile(
        ticker="SSMS",
        plantation_area_ha=100_000,
        ffb_yield_ton_per_ha=22.0,
        oer_pct=0.22,
        hedging_ratio=0.08,
        net_margin=0.14,
        shares_outstanding=9_525_000_000,
        trailing_revenue_idr=7_600_000_000_000,
        downstream_refining=False,
        dmo_allocation_pct=0.20,
    ),
    PlantationCompanyProfile(
        ticker="PALM",
        plantation_area_ha=170_000,
        ffb_yield_ton_per_ha=18.0,
        oer_pct=0.21,
        hedging_ratio=0.10,
        net_margin=0.10,
        shares_outstanding=43_197_500_000,
        trailing_revenue_idr=9_200_000_000_000,
        downstream_refining=False,
        dmo_allocation_pct=0.20,
    ),
]

# CPO reference price in MYR per metric ton (basis for pct change).
_CPO_REFERENCE_PRICE_MYR_PER_TON: float = 3_800.0

# MYR → IDR conversion rate.
_MYR_IDR_RATE: float = 3_500.0


class CPOPlantationStockSensitivity:
    """Model CPO price change → plantation company revenue impact.

    The progressive export levy schedule (post-2022 reform):
        - CPO ref price <= USD 750/ton  → levy  USD 0
        - CPO ref price  750 – 800      → levy USD 55
        - CPO ref price  800 – 850      → levy USD 75
        - CPO ref price  850 – 900      → levy USD 95
        - CPO ref price  900 – 950      → levy USD 115
        - CPO ref price  > 950          → levy USD 140 + USD 5 per USD 50 above

    Args:
        usd_idr_rate: USD/IDR exchange rate for conversions.
        myr_idr_rate: MYR/IDR exchange rate.
        cpo_ref_price_myr: Baseline CPO price in MYR/ton.
    """

    def __init__(
        self,
        usd_idr_rate: float = 15_500.0,
        myr_idr_rate: float = _MYR_IDR_RATE,
        cpo_ref_price_myr: float = _CPO_REFERENCE_PRICE_MYR_PER_TON,
        companies: list[PlantationCompanyProfile] | None = None,
    ) -> None:
        self._usd_idr = usd_idr_rate
        self._myr_idr = myr_idr_rate
        self._cpo_ref_price_myr = cpo_ref_price_myr
        self._companies = companies if companies is not None else _PLANTATION_COMPANIES

    # Export Levy

    @staticmethod
    def _compute_export_levy_usd(cpo_price_usd_per_ton: float) -> float:
        """Compute the progressive export levy in USD per ton.

        Args:
            cpo_price_usd_per_ton: CPO FOB price in USD/ton.

        Returns:
            Export levy in USD per ton.
        """
        if cpo_price_usd_per_ton <= 750.0:
            return 0.0
        if cpo_price_usd_per_ton <= 800.0:
            return 55.0
        if cpo_price_usd_per_ton <= 850.0:
            return 75.0
        if cpo_price_usd_per_ton <= 900.0:
            return 95.0
        if cpo_price_usd_per_ton <= 950.0:
            return 115.0
        # Above USD 950: base 140 + 5 per 50 above 950.
        return 140.0 + 5.0 * ((cpo_price_usd_per_ton - 950.0) / 50.0)

    # Per-company Impact

    def _compute_company_impact(
        self,
        company: PlantationCompanyProfile,
        cpo_price_change_pct: float,
    ) -> StockEarningsImpactEstimate:
        """Compute earnings impact for a single plantation company.

        Args:
            company: Company profile.
            cpo_price_change_pct: CPO price change in percent.

        Returns:
            Earnings impact estimate.
        """
        # Annual CPO production in metric tons.
        annual_cpo_production_ton = company.plantation_area_ha * company.ffb_yield_ton_per_ha * company.oer_pct

        # Price delta in MYR per ton.
        cpo_price_delta_myr = self._cpo_ref_price_myr * (cpo_price_change_pct / 100.0)

        # Convert CPO reference price to USD for levy calculation.
        myr_usd_rate = self._usd_idr / self._myr_idr  # MYR per USD
        cpo_ref_usd = self._cpo_ref_price_myr / myr_usd_rate
        new_cpo_usd = cpo_ref_usd * (1 + cpo_price_change_pct / 100.0)

        # Export levy delta.
        levy_old_usd = self._compute_export_levy_usd(cpo_ref_usd)
        levy_new_usd = self._compute_export_levy_usd(new_cpo_usd)
        levy_delta_usd = levy_new_usd - levy_old_usd
        levy_delta_myr = levy_delta_usd * myr_usd_rate

        # Effective price delta after hedging and DMO.
        export_fraction = 1.0 - company.dmo_allocation_pct
        unhedged_fraction = 1.0 - company.hedging_ratio

        # Revenue impact = production * price_delta * unhedged * export_share
        #                 - production * levy_delta * export_share
        revenue_impact_myr = (annual_cpo_production_ton * cpo_price_delta_myr * unhedged_fraction * export_fraction) - (
            annual_cpo_production_ton * levy_delta_myr * export_fraction
        )

        # DMO production sold at government-set reference → zero price sensitivity.

        revenue_impact_idr = revenue_impact_myr * self._myr_idr
        net_income_impact_idr = revenue_impact_idr * company.net_margin
        eps_impact = net_income_impact_idr / company.shares_outstanding

        impact_pct = (
            abs(revenue_impact_idr) / company.trailing_revenue_idr * 100.0 if company.trailing_revenue_idr > 0 else 0.0
        )

        # Confidence based on hedging transparency and downstream complexity.
        if company.hedging_ratio < 0.10 and not company.downstream_refining:
            confidence = ConfidenceLevel.HIGH
        elif company.downstream_refining:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.HIGH

        return StockEarningsImpactEstimate(
            ticker=company.ticker,
            commodity=CommodityType.CPO,
            revenue_impact_idr=revenue_impact_idr,
            net_income_impact_idr=net_income_impact_idr,
            eps_impact=eps_impact,
            impact_pct_of_revenue=impact_pct,
            confidence=confidence,
            methodology=(
                "plantation_area * ffb_yield * OER * cpo_price_delta * (1 - hedging) * (1 - DMO) - export_levy_delta"
            ),
            assumptions=[
                f"Plantation area: {company.plantation_area_ha:,.0f} ha",
                f"FFB yield: {company.ffb_yield_ton_per_ha} ton/ha",
                f"OER: {company.oer_pct:.0%}",
                f"Hedging ratio: {company.hedging_ratio:.0%}",
                f"DMO allocation: {company.dmo_allocation_pct:.0%}",
                f"Export levy old: USD {levy_old_usd:.1f}/ton, new: USD {levy_new_usd:.1f}/ton",
                f"MYR/IDR: {self._myr_idr:,.0f}",
            ],
        )

    # Public API

    def compute_all_impacts(self, cpo_price_change_pct: float) -> list[StockEarningsImpactEstimate]:
        """Compute impact across all covered plantation stocks.

        Args:
            cpo_price_change_pct: CPO price change in percent.

        Returns:
            List of earnings impact estimates for all plantation tickers.
        """
        estimates: list[StockEarningsImpactEstimate] = []
        for company in self._companies:
            estimate = self._compute_company_impact(company, cpo_price_change_pct)
            logger.info(
                "cpo_company_impact_computed",
                ticker=company.ticker,
                revenue_impact_idr=estimate.revenue_impact_idr,
                eps_impact=estimate.eps_impact,
            )
            estimates.append(estimate)
        return estimates
