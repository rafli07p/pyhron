"""Coal price → miner revenue sensitivity model.

Models the impact of HBA (Harga Batubara Acuan) price changes on
Indonesian coal mining companies listed on IDX.

# TODO: Move hardcoded company profiles and production data to database-backed
# or config-file-based reference data with quarterly update process.

Key regulatory features:
  - Royalty rates are progressive based on coal calorie value and
    mine type (open pit vs underground).
  - DMO (Domestic Market Obligation): 25 % of production must be sold
    domestically at a capped price of USD 90/ton (ESDM regulation).
  - Export duty applies at certain HBA thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass

from commodity_linkage_engine.commodity_to_stock_impact_engine import (
    CommodityType,
    ConfidenceLevel,
    StockEarningsImpactEstimate,
)
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class CoalMinerProfile:
    """Profile for a coal mining company.

    Attributes:
        ticker: IDX ticker symbol.
        annual_production_mt: Annual production in million metric tons.
        avg_calorie_kcal: Average calorie content (GAR kcal/kg).
        cash_cost_usd_per_ton: All-in cash cost in USD/ton.
        royalty_rate: Government royalty as fraction of revenue.
        strip_ratio: Overburden strip ratio.
        net_margin: Approximate net profit margin.
        shares_outstanding: Number of shares.
        trailing_revenue_idr: Trailing 12-month revenue in IDR.
        dmo_pct: Fraction of production under DMO.
        dmo_cap_usd: Maximum price for DMO sales (USD/ton).
    """

    ticker: str
    annual_production_mt: float
    avg_calorie_kcal: int
    cash_cost_usd_per_ton: float
    royalty_rate: float
    strip_ratio: float
    net_margin: float
    shares_outstanding: int
    trailing_revenue_idr: float
    dmo_pct: float = 0.25
    dmo_cap_usd: float = 90.0


_COAL_MINERS: list[CoalMinerProfile] = [
    CoalMinerProfile(
        ticker="ADRO",
        annual_production_mt=60.0,
        avg_calorie_kcal=4_200,
        cash_cost_usd_per_ton=38.0,
        royalty_rate=0.135,
        strip_ratio=5.2,
        net_margin=0.28,
        shares_outstanding=31_985_962_000,
        trailing_revenue_idr=82_000_000_000_000,
    ),
    CoalMinerProfile(
        ticker="PTBA",
        annual_production_mt=30.0,
        avg_calorie_kcal=5_400,
        cash_cost_usd_per_ton=42.0,
        royalty_rate=0.135,
        strip_ratio=4.8,
        net_margin=0.25,
        shares_outstanding=2_304_131_850,
        trailing_revenue_idr=36_500_000_000_000,
    ),
    CoalMinerProfile(
        ticker="ITMG",
        annual_production_mt=22.0,
        avg_calorie_kcal=5_700,
        cash_cost_usd_per_ton=45.0,
        royalty_rate=0.135,
        strip_ratio=6.0,
        net_margin=0.22,
        shares_outstanding=1_129_925_000,
        trailing_revenue_idr=28_000_000_000_000,
    ),
    CoalMinerProfile(
        ticker="BUMI",
        annual_production_mt=85.0,
        avg_calorie_kcal=4_000,
        cash_cost_usd_per_ton=40.0,
        royalty_rate=0.135,
        strip_ratio=5.5,
        net_margin=0.10,
        shares_outstanding=36_627_020_427,
        trailing_revenue_idr=55_000_000_000_000,
    ),
    CoalMinerProfile(
        ticker="HRUM",
        annual_production_mt=12.0,
        avg_calorie_kcal=4_900,
        cash_cost_usd_per_ton=35.0,
        royalty_rate=0.135,
        strip_ratio=4.5,
        net_margin=0.30,
        shares_outstanding=2_703_620_000,
        trailing_revenue_idr=13_000_000_000_000,
    ),
]


class CoalPriceMinerRevenueModel:
    """Model HBA price change → coal miner revenue/earnings impact.

    The DMO obligation requires 25 % of production to be sold domestically
    at max USD 90/ton.  Export sales receive the full HBA-linked price.

    Args:
        usd_idr_rate: USD/IDR exchange rate.
    """

    def __init__(self, usd_idr_rate: float = 15_500.0) -> None:
        self._usd_idr = usd_idr_rate

    @staticmethod
    def _calorie_adjustment_factor(avg_calorie_kcal: int) -> float:
        """Compute calorie-based adjustment vs HBA reference (6,322 kcal GAR).

        Indonesian HBA is based on 6,322 kcal/kg GAR reference.  Lower
        calorie coals trade at a discount proportional to their calorie
        content.

        Args:
            avg_calorie_kcal: Company's average coal calorie (GAR kcal/kg).

        Returns:
            Adjustment factor (0.0 – 1.0+).
        """
        hba_reference_kcal = 6_322
        return avg_calorie_kcal / hba_reference_kcal

    def _compute_company_impact(
        self,
        miner: CoalMinerProfile,
        hba_change_usd_per_ton: float,
    ) -> StockEarningsImpactEstimate:
        """Compute earnings impact for a single coal miner.

        Revenue impact calculation:
            export_vol = production * (1 - dmo_pct)
            dmo_vol = production * dmo_pct
            export_revenue_delta = export_vol * hba_change * cal_adj * (1 - royalty)
            dmo_revenue_delta = 0  (capped at USD 90, insensitive to HBA)

        Args:
            miner: Coal miner profile.
            hba_change_usd_per_ton: HBA price change in USD per ton.

        Returns:
            Earnings impact estimate.
        """
        production_tons = miner.annual_production_mt * 1_000_000

        # Volume split.
        export_vol = production_tons * (1.0 - miner.dmo_pct)
        # dmo_vol sales are capped → zero sensitivity to HBA changes.

        # Calorie-adjusted price change.
        cal_factor = self._calorie_adjustment_factor(miner.avg_calorie_kcal)
        effective_hba_change = hba_change_usd_per_ton * cal_factor

        # Revenue impact on export sales only (after royalty).
        revenue_impact_usd = export_vol * effective_hba_change * (1.0 - miner.royalty_rate)
        revenue_impact_idr = revenue_impact_usd * self._usd_idr

        net_income_impact_idr = revenue_impact_idr * miner.net_margin
        eps_impact = net_income_impact_idr / miner.shares_outstanding

        impact_pct = (
            abs(revenue_impact_idr) / miner.trailing_revenue_idr * 100.0 if miner.trailing_revenue_idr > 0 else 0.0
        )

        # Higher calorie coals have better price discovery → higher confidence.
        confidence = ConfidenceLevel.HIGH if miner.avg_calorie_kcal >= 5_000 else ConfidenceLevel.MEDIUM

        return StockEarningsImpactEstimate(
            ticker=miner.ticker,
            commodity=CommodityType.COAL,
            revenue_impact_idr=revenue_impact_idr,
            net_income_impact_idr=net_income_impact_idr,
            eps_impact=eps_impact,
            impact_pct_of_revenue=impact_pct,
            confidence=confidence,
            methodology=(
                "export_vol * hba_change * calorie_adj * (1 - royalty). "
                "DMO 25% at USD 90/ton cap has zero HBA sensitivity."
            ),
            assumptions=[
                f"Production: {miner.annual_production_mt:.1f} MT/yr",
                f"Avg calorie: {miner.avg_calorie_kcal} kcal/kg GAR",
                f"Calorie adj factor: {cal_factor:.3f}",
                f"Royalty: {miner.royalty_rate:.1%}",
                f"DMO: {miner.dmo_pct:.0%} at USD {miner.dmo_cap_usd}/ton cap",
                f"Cash cost: USD {miner.cash_cost_usd_per_ton}/ton",
                f"USD/IDR: {self._usd_idr:,.0f}",
            ],
        )

    def compute_all_impacts(self, hba_change_usd_per_ton: float) -> list[StockEarningsImpactEstimate]:
        """Compute impact across all covered coal miners.

        Args:
            hba_change_usd_per_ton: HBA price change in USD/ton.

        Returns:
            List of earnings impact estimates for all coal tickers.
        """
        estimates: list[StockEarningsImpactEstimate] = []
        for miner in _COAL_MINERS:
            estimate = self._compute_company_impact(miner, hba_change_usd_per_ton)
            logger.info(
                "coal_company_impact_computed",
                ticker=miner.ticker,
                revenue_impact_idr=estimate.revenue_impact_idr,
                eps_impact=estimate.eps_impact,
            )
            estimates.append(estimate)
        return estimates
