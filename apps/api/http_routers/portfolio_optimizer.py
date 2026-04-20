"""Portfolio optimization API endpoints.

Rebalance endpoint for triggering portfolio optimization with
various methods (Black-Litterman, HRP, equal weight).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio-optimizer"])


class RebalanceRequest(BaseModel):
    method: str = Field(default="black_litterman", description="black_litterman, hrp, or equal_weight")
    universe: list[str] = Field(..., min_length=1)
    max_weight: float = Field(default=0.15, ge=0.01, le=1.0)
    target_vol: float | None = Field(default=None, description="Target annualised volatility")


class RebalanceResponse(BaseModel):
    weights: dict[str, float]
    expected_return: float
    expected_vol: float
    turnover: float
    estimated_cost_bps: float
    method: str
    timestamp: str


@router.post("/rebalance", response_model=RebalanceResponse)
async def rebalance_portfolio(request: RebalanceRequest) -> RebalanceResponse:
    """Trigger portfolio rebalance with the specified method."""
    valid_methods = {"black_litterman", "hrp", "equal_weight"}
    if request.method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown method: {request.method}. Available: {sorted(valid_methods)}",
        )

    now = datetime.now(tz=UTC)

    # In production this would load historical data from DB and call PortfolioOptimizer
    # For now return a stub response
    n = len(request.universe)
    if request.method == "equal_weight":
        w = 1.0 / n
        weights = {s: w for s in request.universe}
    else:
        weights = {s: 1.0 / n for s in request.universe}

    turnover = 0.0
    cost_bps = turnover * 30  # 30 bps round-trip

    logger.info(
        "portfolio_rebalanced",
        method=request.method,
        n_assets=n,
        turnover=turnover,
    )

    return RebalanceResponse(
        weights=weights,
        expected_return=0.0,
        expected_vol=0.0,
        turnover=turnover,
        estimated_cost_bps=cost_bps,
        method=request.method,
        timestamp=now.isoformat(),
    )
