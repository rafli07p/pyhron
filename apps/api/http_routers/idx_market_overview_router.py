"""IDX market overview API endpoints.

Market summary, OHLCV bars, and instrument lookup
for the Indonesia Stock Exchange.
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
router = APIRouter(prefix="/v1/market", tags=["market-data"])


# Response Models
class MarketOverview(BaseModel):
    index_name: str = "IHSG"
    last_value: Decimal
    change: Decimal
    change_pct: float
    volume: int
    value_traded: Decimal
    advances: int
    declines: int
    unchanged: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class InstrumentResponse(BaseModel):
    symbol: str
    name: str
    exchange: str = "IDX"
    sector: str | None = None
    industry: str | None = None
    market_cap: Decimal | None = None
    is_lq45: bool = False
    board: str = "regular"


class OHLCVBar(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    value: Decimal | None = None


# Market Overview
@router.get("/overview", response_model=MarketOverview)
async def get_market_overview() -> MarketOverview:
    """Get current IDX market overview with index value and breadth."""
    # In production: query real-time market data feed
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Market data feed unavailable",
    )


# OHLCV
@router.get("/ohlcv/{symbol}", response_model=list[OHLCVBar])
async def get_ohlcv(
    symbol: str,
    interval: str = Query("1d", pattern="^(1m|5m|15m|1h|1d|1w)$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> list[OHLCVBar]:
    """Get OHLCV bars for a symbol with configurable interval."""
    logger.info("ohlcv_queried", symbol=symbol, interval=interval, limit=limit)
    return []


# Instruments
@router.get("/instruments", response_model=list[InstrumentResponse])
async def list_instruments(
    exchange: str = Query("IDX"),
    sector: str | None = Query(None),
    lq45_only: bool = Query(False),
    board: str | None = Query(None),
) -> list[InstrumentResponse]:
    """List tradeable instruments with optional filters."""
    return []


@router.get("/instruments/{symbol}", response_model=InstrumentResponse)
async def get_instrument(symbol: str) -> InstrumentResponse:
    """Get instrument details by ticker symbol."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Instrument {symbol} not found",
    )
