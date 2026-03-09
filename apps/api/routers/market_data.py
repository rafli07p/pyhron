"""Market data API endpoints.

Stock screener, instrument lookup, OHLCV bars, and news aggregation.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/market", tags=["market-data"])


# ── Response Models ──────────────────────────────────────────────────────────


class InstrumentResponse(BaseModel):
    symbol: str
    name: str
    exchange: str = "IDX"
    sector: str | None = None
    industry: str | None = None
    market_cap: Decimal | None = None
    is_lq45: bool = False


class OHLCVBar(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class ScreenerResult(BaseModel):
    symbol: str
    name: str
    last_price: Decimal
    change_pct: float
    volume: int
    market_cap: Decimal | None = None
    sector: str | None = None


class NewsArticle(BaseModel):
    title: str
    source: str
    url: str
    published_at: datetime
    sentiment: float | None = None
    symbols: list[str] = Field(default_factory=list)


# ── Instrument Lookup ────────────────────────────────────────────────────────


@router.get("/instruments", response_model=list[InstrumentResponse])
async def list_instruments(
    exchange: str = Query("IDX"),
    sector: str | None = Query(None),
    lq45_only: bool = Query(False),
) -> list[InstrumentResponse]:
    """List tradeable instruments with optional filters."""
    return []


@router.get("/instruments/{symbol}", response_model=InstrumentResponse)
async def get_instrument(symbol: str) -> InstrumentResponse:
    """Get instrument details by symbol."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Instrument {symbol} not found",
    )


# ── OHLCV Bars ───────────────────────────────────────────────────────────────


@router.get("/ohlcv/{symbol}", response_model=list[OHLCVBar])
async def get_ohlcv(
    symbol: str,
    interval: str = Query("1d", regex="^(1m|5m|15m|1h|1d|1w)$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> list[OHLCVBar]:
    """Get OHLCV bars for a symbol."""
    return []


# ── Screener ─────────────────────────────────────────────────────────────────


@router.get("/screener", response_model=list[ScreenerResult])
async def screen_stocks(
    min_volume: int | None = Query(None, ge=0),
    min_market_cap: Decimal | None = Query(None),
    sector: str | None = Query(None),
    sort_by: str = Query("volume", regex="^(volume|change_pct|market_cap)$"),
    limit: int = Query(50, ge=1, le=200),
) -> list[ScreenerResult]:
    """Screen stocks by criteria."""
    return []


# ── News ─────────────────────────────────────────────────────────────────────


@router.get("/news", response_model=list[NewsArticle])
async def get_news(
    symbol: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[NewsArticle]:
    """Get aggregated news articles, optionally filtered by symbol."""
    return []
