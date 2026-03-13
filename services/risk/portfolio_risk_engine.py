"""Real-time portfolio risk engine.

Computes portfolio risk metrics every minute during trading hours:
- Parametric VaR (1-day, 5-day, 95% confidence)
- Portfolio Beta (vs IHSG)
- Sector HHI (concentration)
- Concentration metrics (top 5 positions, largest position)
- Daily loss tracking
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class PositionData:
    """Current position data for risk computation."""

    symbol: str
    quantity_shares: int
    avg_cost_idr: Decimal
    last_price_idr: Decimal
    sector: str
    market_value_idr: Decimal


@dataclass
class PortfolioRiskSnapshot:
    """Snapshot of portfolio risk metrics at a point in time."""

    strategy_id: str
    timestamp: datetime
    portfolio_var_1d_pct: Decimal | None
    portfolio_var_5d_pct: Decimal | None
    portfolio_beta: float | None
    sector_hhi: float | None
    gross_exposure_idr: Decimal
    net_exposure_idr: Decimal
    concentration_top5_pct: Decimal | None
    largest_position_pct: Decimal | None
    daily_loss_idr: Decimal | None
    daily_loss_pct: Decimal | None


class PortfolioRiskEngine:
    """Computes real-time portfolio risk metrics.

    VaR uses parametric approach with covariance matrix.
    Beta is computed against IHSG (Indeks Harga Saham Gabungan).
    """

    CONFIDENCE_LEVEL = 0.95
    Z_95 = 1.645
    COVARIANCE_LOOKBACK_DAYS = 60

    def compute_parametric_var(
        self,
        weights: np.ndarray[Any, np.dtype[np.floating[Any]]],
        covariance_matrix: np.ndarray[Any, np.dtype[np.floating[Any]]],
        portfolio_value: Decimal,
        horizon_days: int,
    ) -> Decimal:
        """Compute parametric VaR.

        VaR_1d = portfolio_value * z_95 * portfolio_vol_daily
        portfolio_vol_daily = sqrt(w.T @ Sigma @ w)

        Args:
            weights: position weights (may not sum to 1 for leveraged)
            covariance_matrix: daily return covariance matrix
            portfolio_value: total portfolio value in IDR
            horizon_days: VaR horizon (1 or 5)

        Returns:
            VaR in IDR (positive number representing potential loss).
        """
        if len(weights) == 0:
            return Decimal("0")

        portfolio_variance = float(weights.T @ covariance_matrix @ weights)
        portfolio_vol_daily = portfolio_variance**0.5

        var_daily = float(portfolio_value) * self.Z_95 * portfolio_vol_daily
        var_horizon = var_daily * (horizon_days**0.5)

        return Decimal(str(round(var_horizon, 2)))

    def compute_portfolio_beta(
        self,
        weights: np.ndarray[Any, np.dtype[np.floating[Any]]],
        betas: np.ndarray[Any, np.dtype[np.floating[Any]]],
    ) -> float:
        """Compute weighted portfolio beta vs IHSG."""
        if len(weights) == 0 or len(betas) == 0:
            return 0.0
        return float(np.dot(weights, betas))

    def compute_sector_hhi(
        self,
        positions: dict[str, PositionData],
        sector_map: dict[str, str],
        nav_idr: Decimal,
    ) -> float:
        """Compute Herfindahl-Hirschman Index for sector concentration.

        HHI = sum(s_k^2) where s_k = sector weight
        HHI = 1.0 means 100% in one sector
        HHI = 1/N means perfectly diversified across N sectors
        """
        if not positions or nav_idr <= 0:
            return 0.0

        sector_exposure: dict[str, Decimal] = {}
        for symbol, pos in positions.items():
            sector = sector_map.get(symbol, "Unknown")
            sector_exposure[sector] = sector_exposure.get(sector, Decimal("0")) + pos.market_value_idr

        hhi = 0.0
        for exposure in sector_exposure.values():
            weight = float(exposure / nav_idr)
            hhi += weight * weight

        return round(hhi, 4)

    async def compute_snapshot(
        self,
        strategy_id: str,
        positions: dict[str, PositionData],
        nav_idr: Decimal,
        nav_start_of_day_idr: Decimal | None = None,
        db_session: AsyncSession | None = None,
    ) -> PortfolioRiskSnapshot:
        """Compute all risk metrics for current positions.

        Returns snapshot (does not persist to DB -- caller decides).
        """
        now = datetime.now(UTC)

        # Compute gross and net exposure
        gross_exposure = Decimal("0")
        net_exposure = Decimal("0")
        for pos in positions.values():
            gross_exposure += abs(pos.market_value_idr)
            net_exposure += pos.market_value_idr

        # Compute concentration metrics
        sorted_positions = sorted(positions.values(), key=lambda p: abs(p.market_value_idr), reverse=True)

        largest_pct = None
        top5_pct = None
        if sorted_positions and nav_idr > 0:
            largest_pct = Decimal(str(round(float(abs(sorted_positions[0].market_value_idr) / nav_idr) * 100, 2)))
            top5_sum = sum(abs(p.market_value_idr) for p in sorted_positions[:5])
            top5_pct = Decimal(str(round(float(top5_sum / nav_idr) * 100, 2)))

        # Sector HHI
        sector_map = {sym: pos.sector for sym, pos in positions.items()}
        hhi = self.compute_sector_hhi(positions, sector_map, nav_idr)

        # Daily loss
        daily_loss_idr = None
        daily_loss_pct = None
        if nav_start_of_day_idr is not None and nav_start_of_day_idr > 0:
            daily_loss_idr = nav_start_of_day_idr - nav_idr
            daily_loss_pct = Decimal(str(round(float(daily_loss_idr / nav_start_of_day_idr) * 100, 4)))

        return PortfolioRiskSnapshot(
            strategy_id=strategy_id,
            timestamp=now,
            portfolio_var_1d_pct=None,  # Requires historical returns data
            portfolio_var_5d_pct=None,
            portfolio_beta=None,  # Requires IHSG returns data
            sector_hhi=hhi,
            gross_exposure_idr=gross_exposure,
            net_exposure_idr=net_exposure,
            concentration_top5_pct=top5_pct,
            largest_position_pct=largest_pct,
            daily_loss_idr=daily_loss_idr,
            daily_loss_pct=daily_loss_pct,
        )
