"""Nickel price → nickel producer revenue sensitivity model.

Models the impact of LME nickel price changes on Indonesian nickel
producers listed on IDX.

Product mix matters significantly:
  - INCO: Nickel matte (high-grade, strong LME correlation ~0.85).
  - ANTM: Ferronickel (partial LME correlation ~0.55, also gold/bauxite).
  - MDKA: Growing nickel exposure via HPAL, also gold.

Indonesia's nickel export ban on raw ore (since 2020) means all
producers sell processed products with varying correlations to LME.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.structured_json_logger import get_logger

from commodity_linkage_engine.commodity_to_stock_impact_engine import (
    ConfidenceLevel,
    CommodityType,
    StockEarningsImpactEstimate,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class NickelProducerProfile:
    """Profile for a nickel producer.

    Attributes:
        ticker: IDX ticker symbol.
        nickel_production_ton: Annual nickel-in-product production (tons).
        product_type: Primary nickel product form.
        lme_correlation: Correlation of company ASP to LME nickel price.
        nickel_revenue_share: Fraction of total revenue from nickel.
        cash_cost_usd_per_ton: Cash cost of nickel production.
        royalty_rate: Government royalty rate.
        net_margin: Approximate net profit margin.
        shares_outstanding: Number of shares.
        trailing_revenue_idr: Trailing 12-month revenue in IDR.
    """

    ticker: str
    nickel_production_ton: float
    product_type: str
    lme_correlation: float
    nickel_revenue_share: float
    cash_cost_usd_per_ton: float
    royalty_rate: float
    net_margin: float
    shares_outstanding: int
    trailing_revenue_idr: float


_NICKEL_PRODUCERS: list[NickelProducerProfile] = [
    NickelProducerProfile(
        ticker="INCO",
        nickel_production_ton=72_000,
        product_type="nickel_matte",
        lme_correlation=0.85,
        nickel_revenue_share=0.98,
        cash_cost_usd_per_ton=11_500,
        royalty_rate=0.10,
        net_margin=0.25,
        shares_outstanding=9_936_338_720,
        trailing_revenue_idr=18_500_000_000_000,
    ),
    NickelProducerProfile(
        ticker="ANTM",
        nickel_production_ton=25_000,
        product_type="ferronickel",
        lme_correlation=0.55,
        nickel_revenue_share=0.35,
        cash_cost_usd_per_ton=13_000,
        royalty_rate=0.10,
        net_margin=0.08,
        shares_outstanding=24_030_764_725,
        trailing_revenue_idr=32_000_000_000_000,
    ),
    NickelProducerProfile(
        ticker="MDKA",
        nickel_production_ton=18_000,
        product_type="mixed_hydroxide_precipitate",
        lme_correlation=0.65,
        nickel_revenue_share=0.40,
        cash_cost_usd_per_ton=12_000,
        royalty_rate=0.10,
        net_margin=0.15,
        shares_outstanding=21_524_025_000,
        trailing_revenue_idr=14_000_000_000_000,
    ),
]


class NickelPriceMinerRevenueModel:
    """Model LME nickel price change → nickel producer revenue impact.

    Because Indonesian producers sell processed products (matte,
    ferronickel, MHP) rather than pure LME-grade nickel, each company
    has a different correlation coefficient to LME.

    Revenue impact formula:
        delta = production_ton * lme_change * lme_correlation
                * nickel_rev_share * (1 - royalty)

    Args:
        usd_idr_rate: USD/IDR exchange rate.
    """

    def __init__(self, usd_idr_rate: float = 15_500.0) -> None:
        self._usd_idr = usd_idr_rate

    def _compute_company_impact(
        self,
        producer: NickelProducerProfile,
        lme_change_usd_per_ton: float,
    ) -> StockEarningsImpactEstimate:
        """Compute earnings impact for a single nickel producer.

        Args:
            producer: Nickel producer profile.
            lme_change_usd_per_ton: LME nickel price change in USD/ton.

        Returns:
            Earnings impact estimate.
        """
        # Effective price change adjusted for product-LME correlation.
        effective_price_change = lme_change_usd_per_ton * producer.lme_correlation

        # Revenue impact from nickel segment only.
        revenue_impact_usd = (
            producer.nickel_production_ton
            * effective_price_change
            * (1.0 - producer.royalty_rate)
        )

        revenue_impact_idr = revenue_impact_usd * self._usd_idr
        net_income_impact_idr = revenue_impact_idr * producer.net_margin
        eps_impact = net_income_impact_idr / producer.shares_outstanding

        impact_pct = (
            abs(revenue_impact_idr) / producer.trailing_revenue_idr * 100.0
            if producer.trailing_revenue_idr > 0
            else 0.0
        )

        # Confidence is driven by LME correlation strength.
        if producer.lme_correlation >= 0.80:
            confidence = ConfidenceLevel.HIGH
        elif producer.lme_correlation >= 0.60:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        return StockEarningsImpactEstimate(
            ticker=producer.ticker,
            commodity=CommodityType.NICKEL,
            revenue_impact_idr=revenue_impact_idr,
            net_income_impact_idr=net_income_impact_idr,
            eps_impact=eps_impact,
            impact_pct_of_revenue=impact_pct,
            confidence=confidence,
            methodology=(
                f"production * lme_change * correlation({producer.lme_correlation:.2f}) "
                f"* (1 - royalty). Product: {producer.product_type}."
            ),
            assumptions=[
                f"Ni production: {producer.nickel_production_ton:,.0f} ton/yr",
                f"Product type: {producer.product_type}",
                f"LME correlation: {producer.lme_correlation:.2f}",
                f"Nickel revenue share: {producer.nickel_revenue_share:.0%}",
                f"Royalty: {producer.royalty_rate:.0%}",
                f"Cash cost: USD {producer.cash_cost_usd_per_ton:,.0f}/ton",
                f"USD/IDR: {self._usd_idr:,.0f}",
            ],
        )

    def compute_all_impacts(
        self, lme_change_usd_per_ton: float
    ) -> list[StockEarningsImpactEstimate]:
        """Compute impact across all covered nickel producers.

        Args:
            lme_change_usd_per_ton: LME nickel price change in USD/ton.

        Returns:
            List of earnings impact estimates for all nickel tickers.
        """
        estimates: list[StockEarningsImpactEstimate] = []
        for producer in _NICKEL_PRODUCERS:
            estimate = self._compute_company_impact(producer, lme_change_usd_per_ton)
            logger.info(
                "nickel_company_impact_computed",
                ticker=producer.ticker,
                revenue_impact_idr=estimate.revenue_impact_idr,
            )
            estimates.append(estimate)
        return estimates
