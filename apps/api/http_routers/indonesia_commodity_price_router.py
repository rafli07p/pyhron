"""Indonesia commodity price API endpoints.

Commodity prices and trends for key Indonesian commodities
including palm oil, coal, nickel, tin, rubber, and crude oil.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from decimal import Decimal

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/commodities", tags=["commodities"])


# ── Response Models ──────────────────────────────────────────────────────────


class CommodityPrice(BaseModel):
    code: str = Field(description="e.g. CPO, COAL_NEX, NICKEL, TIN, RUBBER")
    name: str
    last_price: Decimal
    currency: str = "USD"
    unit: str = Field(description="e.g. USD/MT, USD/bbl")
    change_pct: float
    change_1w_pct: float | None = None
    change_1m_pct: float | None = None
    updated_at: datetime


class CommodityHistoryPoint(BaseModel):
    date: date
    price: Decimal
    volume: int | None = None


class CommodityHistory(BaseModel):
    code: str
    name: str
    currency: str
    unit: str
    data_points: list[CommodityHistoryPoint]


class CommodityDashboard(BaseModel):
    commodities: list[CommodityPrice]
    last_updated: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[CommodityPrice])
async def list_commodities(
    category: str | None = Query(None, description="energy, metals, agriculture"),
) -> list[CommodityPrice]:
    """Get latest prices for all tracked commodities."""
    logger.info("commodities_queried", category=category)
    return []


@router.get("/dashboard", response_model=CommodityDashboard)
async def get_commodity_dashboard() -> CommodityDashboard:
    """Get commodity dashboard with all prices and trends."""
    return CommodityDashboard(commodities=[])


@router.get("/{commodity_code}/history", response_model=CommodityHistory)
async def get_commodity_history(
    commodity_code: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> CommodityHistory:
    """Get historical price data for a specific commodity."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Commodity {commodity_code} not found",
    )
