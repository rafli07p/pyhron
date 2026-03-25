"""Post-trade analytics for the Enthropy trading platform.

Calculates slippage, market impact, and generates execution quality
reports using pandas for efficient batch analytics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import structlog

from shared.schemas.order_events import OrderFill, OrderSide

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class SlippageResult:
    """Slippage analysis for a single fill or batch of fills."""

    symbol: str
    expected_price: Decimal
    fill_price: Decimal
    slippage_bps: float
    slippage_dollars: Decimal
    side: str


@dataclass
class MarketImpactResult:
    """Market impact analysis result."""

    symbol: str
    pre_trade_price: Decimal
    post_trade_price: Decimal
    vwap: Decimal
    fill_price: Decimal
    temporary_impact_bps: float
    permanent_impact_bps: float
    total_impact_bps: float
    participation_rate: float  # fill_qty / total_volume


@dataclass
class ExecutionQualityReport:
    """Aggregated execution quality report for a tenant."""

    tenant_id: str
    report_date: str
    total_orders: int
    total_fills: int
    total_volume: Decimal
    avg_slippage_bps: float
    median_slippage_bps: float
    p95_slippage_bps: float
    avg_market_impact_bps: float
    fill_rate: float  # fills / orders
    symbols_traded: list[str]
    slippage_by_symbol: dict[str, float]
    slippage_by_side: dict[str, float]
    summary_df: pd.DataFrame | None = None


# ---------------------------------------------------------------------------
# Analytics engine
# ---------------------------------------------------------------------------

class PostTradeAnalytics:
    """Post-trade analytics with pandas-based batch processing.

    Analyses are performed over collections of fills and market data
    snapshots to produce slippage, impact, and quality metrics.

    Parameters
    ----------
    None — this service is stateless; all data is passed per call.
    """

    def __init__(self) -> None:
        self._log = logger.bind(component="PostTradeAnalytics")

    # -- Slippage ------------------------------------------------------------

    def calculate_slippage(
        self,
        tenant_id: str,
        fills: list[OrderFill],
        expected_prices: dict[str, Decimal],
    ) -> list[SlippageResult]:
        """Calculate slippage for a batch of fills.

        Slippage is the difference between the expected (decision) price
        and the actual fill price, expressed in basis points.

        Parameters
        ----------
        fills:
            List of order fills to analyse.
        expected_prices:
            Mapping symbol -> expected/decision price at order time.

        Returns
        -------
        list[SlippageResult]
            One result per fill.
        """
        self._log.info("calculate_slippage", tenant_id=tenant_id, num_fills=len(fills))
        results: list[SlippageResult] = []

        for fill in fills:
            expected = expected_prices.get(fill.symbol, fill.fill_price)
            if expected == Decimal("0"):
                continue

            diff = fill.fill_price - expected
            # For sells, positive diff = less slippage
            if fill.side == OrderSide.SELL:
                diff = -diff

            slippage_bps = float(diff / expected) * 10_000
            slippage_dollars = diff * fill.fill_qty

            results.append(SlippageResult(
                symbol=fill.symbol,
                expected_price=expected,
                fill_price=fill.fill_price,
                slippage_bps=round(slippage_bps, 2),
                slippage_dollars=slippage_dollars,
                side=fill.side.value,
            ))

        return results

    # -- Market impact -------------------------------------------------------

    def calculate_market_impact(
        self,
        tenant_id: str,
        fills: list[OrderFill],
        pre_trade_prices: dict[str, Decimal],
        post_trade_prices: dict[str, Decimal],
        vwap_prices: dict[str, Decimal],
        total_volumes: dict[str, Decimal],
    ) -> list[MarketImpactResult]:
        """Estimate market impact using the Almgren-Chriss decomposition.

        Temporary impact = fill_price - VWAP
        Permanent impact  = post_trade_price - pre_trade_price

        Parameters
        ----------
        pre_trade_prices:
            Prices immediately before the order.
        post_trade_prices:
            Prices shortly after the last fill.
        vwap_prices:
            Volume-weighted average price during the execution window.
        total_volumes:
            Total market volume during the execution window.
        """
        self._log.info("calculate_market_impact", tenant_id=tenant_id, num_fills=len(fills))
        results: list[MarketImpactResult] = []

        # Aggregate fills per symbol
        symbol_fills: dict[str, list[OrderFill]] = {}
        for fill in fills:
            symbol_fills.setdefault(fill.symbol, []).append(fill)

        for symbol, sym_fills in symbol_fills.items():
            pre = pre_trade_prices.get(symbol, Decimal("0"))
            post = post_trade_prices.get(symbol, Decimal("0"))
            vwap = vwap_prices.get(symbol, Decimal("0"))
            total_vol = total_volumes.get(symbol, Decimal("1"))

            if pre == Decimal("0") or vwap == Decimal("0"):
                continue

            # Weighted average fill price
            total_qty = sum((f.fill_qty for f in sym_fills), Decimal("0"))
            wavg_fill = sum((f.fill_price * f.fill_qty for f in sym_fills), Decimal("0")) / total_qty

            direction = 1 if sym_fills[0].side == OrderSide.BUY else -1

            temp_impact_bps = float((wavg_fill - vwap) / vwap) * 10_000 * direction
            perm_impact_bps = float((post - pre) / pre) * 10_000 * direction
            total_impact_bps = temp_impact_bps + perm_impact_bps

            participation = float(total_qty / total_vol) if total_vol > 0 else 0.0

            results.append(MarketImpactResult(
                symbol=symbol,
                pre_trade_price=pre,
                post_trade_price=post,
                vwap=vwap,
                fill_price=wavg_fill,
                temporary_impact_bps=round(temp_impact_bps, 2),
                permanent_impact_bps=round(perm_impact_bps, 2),
                total_impact_bps=round(total_impact_bps, 2),
                participation_rate=round(participation, 4),
            ))

        return results

    # -- Execution quality report --------------------------------------------

    def execution_quality_report(
        self,
        tenant_id: str,
        fills: list[OrderFill],
        expected_prices: dict[str, Decimal],
        total_orders: int | None = None,
        report_date: str | None = None,
    ) -> ExecutionQualityReport:
        """Generate a comprehensive execution quality report.

        Builds a pandas DataFrame of all fills, computes slippage
        statistics, and aggregates by symbol and side.

        Parameters
        ----------
        fills:
            All fills to include in the report.
        expected_prices:
            Decision/benchmark prices for slippage calculation.
        total_orders:
            Total orders submitted (for fill-rate calculation).
        report_date:
            Date label for the report.
        """
        self._log.info("execution_quality_report", tenant_id=tenant_id, num_fills=len(fills))
        rpt_date = report_date or datetime.now(UTC).strftime("%Y-%m-%d")

        if not fills:
            return ExecutionQualityReport(
                tenant_id=tenant_id,
                report_date=rpt_date,
                total_orders=total_orders or 0,
                total_fills=0,
                total_volume=Decimal("0"),
                avg_slippage_bps=0.0,
                median_slippage_bps=0.0,
                p95_slippage_bps=0.0,
                avg_market_impact_bps=0.0,
                fill_rate=0.0,
                symbols_traded=[],
                slippage_by_symbol={},
                slippage_by_side={},
            )

        # Build DataFrame
        rows = []
        for fill in fills:
            expected = expected_prices.get(fill.symbol, fill.fill_price)
            diff = fill.fill_price - expected
            if fill.side == OrderSide.SELL:
                diff = -diff
            slippage_bps = float(diff / expected) * 10_000 if expected != Decimal("0") else 0.0

            rows.append({
                "symbol": fill.symbol,
                "side": fill.side.value,
                "fill_qty": float(fill.fill_qty),
                "fill_price": float(fill.fill_price),
                "expected_price": float(expected),
                "slippage_bps": slippage_bps,
                "notional": float(fill.fill_qty * fill.fill_price),
                "commission": float(fill.commission),
            })

        df = pd.DataFrame(rows)

        total_volume = Decimal(str(round(df["notional"].sum(), 2)))
        slippage_arr = df["slippage_bps"].to_numpy()

        # Aggregations
        slippage_by_symbol: dict[str, float] = (
            df.groupby("symbol")["slippage_bps"].mean().round(2).to_dict()
        )
        slippage_by_side: dict[str, float] = (
            df.groupby("side")["slippage_bps"].mean().round(2).to_dict()
        )

        symbols_traded = sorted(df["symbol"].unique().tolist())
        n_orders = total_orders if total_orders is not None else len(fills)
        fill_rate = len(fills) / n_orders if n_orders > 0 else 0.0

        return ExecutionQualityReport(
            tenant_id=tenant_id,
            report_date=rpt_date,
            total_orders=n_orders,
            total_fills=len(fills),
            total_volume=total_volume,
            avg_slippage_bps=round(float(np.mean(slippage_arr)), 2),
            median_slippage_bps=round(float(np.median(slippage_arr)), 2),
            p95_slippage_bps=round(float(np.percentile(slippage_arr, 95)), 2),
            avg_market_impact_bps=0.0,  # requires separate market data
            fill_rate=round(fill_rate, 4),
            symbols_traded=symbols_traded,
            slippage_by_symbol=slippage_by_symbol,
            slippage_by_side=slippage_by_side,
            summary_df=df,
        )


__all__ = [
    "ExecutionQualityReport",
    "MarketImpactResult",
    "PostTradeAnalytics",
    "SlippageResult",
]
