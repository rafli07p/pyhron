"""IDX equity stock detail API endpoints.

Single stock deep dive: profile, financials, corporate actions,
and ownership structure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/stocks", tags=["stock-detail"])


# Response Models
class StockProfile(BaseModel):
    symbol: str
    name: str
    exchange: str = "IDX"
    sector: str | None = None
    industry: str | None = None
    listing_date: date | None = None
    market_cap: Decimal | None = None
    last_price: Decimal | None = None
    shares_outstanding: int | None = None
    is_lq45: bool = False
    description: str | None = None


class FinancialSummary(BaseModel):
    symbol: str
    period: str
    revenue: Decimal | None = None
    net_income: Decimal | None = None
    total_assets: Decimal | None = None
    total_equity: Decimal | None = None
    eps: Decimal | None = None
    pe_ratio: float | None = None
    pbv_ratio: float | None = None
    roe: float | None = None
    der: float | None = None


class CorporateAction(BaseModel):
    symbol: str
    action_type: str = Field(description="dividend, stock_split, rights_issue, etc.")
    ex_date: date
    record_date: date | None = None
    description: str
    value: Decimal | None = None


class OwnershipEntry(BaseModel):
    holder_name: str
    holder_type: str = Field(description="institution, insider, public")
    shares_held: int
    ownership_pct: float
    change_from_prior: float | None = None


# Endpoints
@router.get("/{symbol}", response_model=StockProfile)
async def get_stock_profile(symbol: str) -> StockProfile:
    """Get comprehensive stock profile by ticker symbol."""
    logger.info("stock_profile_queried", symbol=symbol)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Stock {symbol} not found",
    )


@router.get("/{symbol}/financials", response_model=list[FinancialSummary])
async def get_financials(
    symbol: str,
    period_type: str = Query("annual", pattern="^(annual|quarterly)$"),
    limit: int = Query(8, ge=1, le=20),
) -> list[FinancialSummary]:
    """Get historical financial statements for a stock."""
    logger.info("financials_queried", symbol=symbol, period_type=period_type)
    return []


@router.get("/{symbol}/corporate-actions", response_model=list[CorporateAction])
async def get_corporate_actions(
    symbol: str,
    action_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[CorporateAction]:
    """Get corporate actions history (dividends, splits, rights issues)."""
    return []


@router.get("/{symbol}/ownership", response_model=list[OwnershipEntry])
async def get_ownership(symbol: str) -> list[OwnershipEntry]:
    """Get ownership breakdown for a stock."""
    return []
