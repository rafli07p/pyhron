"""Commodity-to-stock impact analysis API endpoints.

Analyzes how commodity price movements affect Indonesian equities,
providing sensitivity matrices, impact alerts, and correlation data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/commodity-impact", tags=["commodity-impact"])


# ── Response Models ──────────────────────────────────────────────────────────


class StockImpact(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    correlation: float = Field(description="Correlation coefficient with commodity")
    beta: float = Field(description="Sensitivity to commodity price changes")
    revenue_exposure_pct: float | None = Field(
        None, description="Estimated revenue exposure to commodity"
    )


class CommodityImpactAnalysis(BaseModel):
    commodity_code: str
    commodity_name: str
    change_pct_30d: float | None = None
    impacted_stocks: list[StockImpact]
    analysis_date: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class ImpactAlert(BaseModel):
    id: str
    commodity_code: str
    commodity_name: str
    symbol: str
    alert_type: str = Field(description="price_spike, correlation_break, threshold_breach")
    severity: str = Field(description="low, medium, high")
    message: str
    created_at: datetime


class SensitivityCell(BaseModel):
    symbol: str
    commodity_code: str
    beta: float
    correlation: float
    r_squared: float


class SensitivityMatrix(BaseModel):
    commodities: list[str]
    stocks: list[str]
    cells: list[SensitivityCell]
    computed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/analysis/{commodity_code}", response_model=CommodityImpactAnalysis)
async def get_impact_analysis(
    commodity_code: str,
    min_correlation: float = Query(0.3, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
) -> CommodityImpactAnalysis:
    """Get stocks impacted by a specific commodity's price movement."""
    logger.info("impact_analysis_queried", commodity_code=commodity_code)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Commodity {commodity_code} not found",
    )


@router.get("/alerts", response_model=list[ImpactAlert])
async def get_impact_alerts(
    commodity_code: str | None = Query(None),
    severity: str | None = Query(None, pattern="^(low|medium|high)$"),
    limit: int = Query(20, ge=1, le=100),
) -> list[ImpactAlert]:
    """Get active commodity impact alerts."""
    return []


@router.get("/sensitivity-matrix", response_model=SensitivityMatrix)
async def get_sensitivity_matrix(
    commodities: str | None = Query(None, description="Comma-separated commodity codes"),
    symbols: str | None = Query(None, description="Comma-separated stock symbols"),
) -> SensitivityMatrix:
    """Get commodity-stock sensitivity matrix with beta and correlation."""
    commodity_list = commodities.split(",") if commodities else []
    symbol_list = symbols.split(",") if symbols else []
    logger.info("sensitivity_matrix_queried", commodities=commodity_list, symbols=symbol_list)
    return SensitivityMatrix(
        commodities=commodity_list,
        stocks=symbol_list,
        cells=[],
    )
