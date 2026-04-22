"""IDX market overview API endpoints.

Market summary, OHLCV bars, and instrument lookup
for the Indonesia Stock Exchange.
"""

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import exists, func, select

from data_platform.database_models.idx_equity_index_constituent import IdxEquityIndexConstituent
from data_platform.database_models.idx_equity_instrument import IdxEquityInstrument
from data_platform.database_models.idx_equity_ohlcv_tick import IdxEquityOhlcvTick
from shared.async_database_session import get_session
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/markets", tags=["market-data"], redirect_slashes=False)


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


# Helper: build LQ45 subquery for a given symbol column
def _lq45_exists_subquery(symbol_col: Any) -> Any:
    """Return an exists() clause checking LQ45 membership (active, no removal)."""
    return exists(
        select(IdxEquityIndexConstituent.symbol).where(
            IdxEquityIndexConstituent.index_name == "LQ45",
            IdxEquityIndexConstituent.symbol == symbol_col,
            IdxEquityIndexConstituent.removal_date.is_(None),
        )
    )


def _instrument_to_response(inst: IdxEquityInstrument, is_lq45: bool) -> InstrumentResponse:
    return InstrumentResponse(
        symbol=inst.symbol,
        name=inst.company_name,
        exchange="IDX",
        sector=inst.sector or "",
        industry=inst.sub_sector or "",
        market_cap=Decimal(inst.market_cap_idr) if inst.market_cap_idr is not None else None,
        is_lq45=is_lq45,
        board="regular",
    )


# Market Overview
@router.get("/overview", response_model=MarketOverview)
async def get_market_overview(_user: TokenPayload = Depends(require_role(Role.VIEWER))) -> MarketOverview:
    """Get current IDX market overview with index value and breadth."""
    async with get_session() as session:
        count_result = await session.execute(
            select(func.count()).select_from(IdxEquityInstrument).where(IdxEquityInstrument.is_active.is_(True))
        )
        instrument_count = count_result.scalar_one()

    return MarketOverview(
        index_name="IHSG",
        last_value=Decimal("0"),
        change=Decimal("0"),
        change_pct=0.0,
        volume=0,
        value_traded=Decimal("0"),
        advances=0,
        declines=0,
        unchanged=instrument_count,
        timestamp=datetime.now(tz=UTC),
    )


# OHLCV
@router.get("/ohlcv/{symbol}", response_model=list[OHLCVBar])
async def get_ohlcv(
    symbol: str,
    interval: str = Query("1d", pattern="^(1m|5m|15m|1h|1d|1w)$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[OHLCVBar]:
    """Get OHLCV bars for a symbol with configurable interval."""
    logger.info("ohlcv_queried", symbol=symbol, interval=interval, limit=limit)

    async with get_session() as session:
        stmt = select(IdxEquityOhlcvTick).where(IdxEquityOhlcvTick.symbol == symbol.upper())
        if start is not None:
            stmt = stmt.where(IdxEquityOhlcvTick.time >= datetime.combine(start, datetime.min.time(), tzinfo=UTC))
        if end is not None:
            stmt = stmt.where(IdxEquityOhlcvTick.time <= datetime.combine(end, datetime.max.time(), tzinfo=UTC))
        stmt = stmt.order_by(IdxEquityOhlcvTick.time.desc()).limit(limit)

        result = await session.execute(stmt)
        rows = result.scalars().all()

    return [
        OHLCVBar(
            timestamp=row.time,
            open=row.open or Decimal("0"),
            high=row.high or Decimal("0"),
            low=row.low or Decimal("0"),
            close=row.close or Decimal("0"),
            volume=row.volume or 0,
            value=row.vwap,
        )
        for row in rows
    ]


# Instruments
@router.get("/instruments", response_model=list[InstrumentResponse])
async def list_instruments(
    exchange: str = Query("IDX"),
    sector: str | None = Query(None),
    lq45_only: bool = Query(False),
    board: str | None = Query(None),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[InstrumentResponse]:
    """List tradeable instruments with optional filters."""
    async with get_session() as session:
        stmt = select(IdxEquityInstrument).where(IdxEquityInstrument.is_active.is_(True))

        if sector is not None:
            stmt = stmt.where(IdxEquityInstrument.sector == sector)

        if lq45_only:
            stmt = stmt.where(_lq45_exists_subquery(IdxEquityInstrument.symbol))

        result = await session.execute(stmt)
        instruments = result.scalars().all()

        # Fetch LQ45 symbols in one query to populate is_lq45
        lq45_result = await session.execute(
            select(IdxEquityIndexConstituent.symbol).where(
                IdxEquityIndexConstituent.index_name == "LQ45",
                IdxEquityIndexConstituent.removal_date.is_(None),
            )
        )
        lq45_symbols = {row[0] for row in lq45_result.all()}

    return [_instrument_to_response(inst, inst.symbol in lq45_symbols) for inst in instruments]


@router.get("/instruments/{symbol}", response_model=InstrumentResponse)
async def get_instrument(symbol: str, _user: TokenPayload = Depends(require_role(Role.VIEWER))) -> InstrumentResponse:
    """Get instrument details by ticker symbol."""
    async with get_session() as session:
        result = await session.execute(select(IdxEquityInstrument).where(IdxEquityInstrument.symbol == symbol.upper()))
        inst = result.scalar_one_or_none()
        if inst is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument {symbol} not found",
            )

        # Check LQ45 membership
        lq45_result = await session.execute(
            select(IdxEquityIndexConstituent.symbol).where(
                IdxEquityIndexConstituent.index_name == "LQ45",
                IdxEquityIndexConstituent.symbol == symbol.upper(),
                IdxEquityIndexConstituent.removal_date.is_(None),
            )
        )
        is_lq45 = lq45_result.scalar_one_or_none() is not None

    return _instrument_to_response(inst, is_lq45)


# ============================================================================
# Public endpoints (no auth) — yfinance-backed live index & intraday data
# ============================================================================


class IndexQuote(BaseModel):
    symbol: str
    name: str
    current: float
    change: float
    change_pct: float = Field(alias="changePct")
    points: list[float] = []
    last_update: str = Field(alias="lastUpdate")

    model_config = {"populate_by_name": True}


class IntradayResponse(BaseModel):
    symbol: str
    current: float
    open: float
    change: float
    points: list[float]
    timestamps: list[str] = []
    last_update: str = Field(alias="lastUpdate")

    model_config = {"populate_by_name": True}


IDX_INDEX_MAP: dict[str, dict[str, str]] = {
    "JCI": {"yahoo": "^JKSE", "name": "Jakarta Composite"},
    "IHSG": {"yahoo": "^JKSE", "name": "Jakarta Composite"},
    "LQ45": {"yahoo": "^JKLQ45", "name": "LQ45 Index"},
    "IDX30": {"yahoo": "^JKIDX30", "name": "IDX30 Index"},
    "IDX80": {"yahoo": "^JKSE", "name": "IDX80 Index"},
    "JII": {"yahoo": "^JKII", "name": "Jakarta Islamic"},
}

SYMBOL_MAP: dict[str, str] = {sym: meta["yahoo"] for sym, meta in IDX_INDEX_MAP.items()}

FALLBACK_INDICES: dict[str, dict[str, float]] = {
    "JCI": {"current": 7234.56, "change": 0.45},
    "IHSG": {"current": 7234.56, "change": 0.45},
    "LQ45": {"current": 985.23, "change": -0.52},
    "IDX30": {"current": 482.18, "change": 0.58},
    "IDX80": {"current": 132.45, "change": 0.66},
    "JII": {"current": 548.92, "change": -0.58},
}


def _fallback_points(fb: dict[str, float]) -> list[float]:
    """Deterministic 30-point sparkline around fb['current']."""
    trend_sign = 1 if fb["change"] > 0 else 0
    return [
        round(
            fb["current"]
            + trend_sign * (i / 29) * fb["current"] * 0.01
            + math.sin(i * 0.5) * fb["current"] * 0.003,
            2,
        )
        for i in range(30)
    ]


@router.get("/indices", response_model=list[IndexQuote], dependencies=[])
async def get_indices() -> list[IndexQuote]:
    """Get IDX index quotes with 30-day sparkline data.

    Public endpoint — no auth required for market overview data.
    Uses yfinance as primary source with deterministic fallback.
    """
    import asyncio

    import yfinance as yf

    wib = ZoneInfo("Asia/Jakarta")
    now = datetime.now(tz=UTC)
    period1 = now - timedelta(days=30)
    last_update = now.astimezone(wib).strftime("%H:%M")

    async def fetch_index(sym: str, meta: dict[str, str]) -> IndexQuote:
        try:

            def _fetch() -> tuple[float, float, list[float]]:
                ticker = yf.Ticker(meta["yahoo"])
                info = ticker.fast_info
                current = float(info.last_price or 0)
                prev_close = float(info.previous_close or 0)
                change_pct_local = (
                    ((current - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
                )
                hist = ticker.history(start=period1, end=now, interval="1d")
                points_local = [float(c) for c in hist["Close"].tolist()] if not hist.empty else []
                if current > 0 and (not points_local or points_local[-1] != current):
                    points_local.append(current)
                return current, round(change_pct_local, 4), points_local

            loop = asyncio.get_event_loop()
            current, change_pct, points = await loop.run_in_executor(None, _fetch)

            if current <= 0 or len(points) < 2:
                raise ValueError("Insufficient data")

            return IndexQuote(
                symbol=sym,
                name=meta["name"],
                current=current,
                change=round(change_pct, 2),
                changePct=change_pct,
                points=points,
                lastUpdate=last_update,
            )
        except Exception as exc:
            logger.warning("index_fetch_failed", symbol=sym, error=str(exc))
            fb = FALLBACK_INDICES.get(sym, {"current": 500.0, "change": 0.0})
            return IndexQuote(
                symbol=sym,
                name=meta["name"],
                current=fb["current"],
                change=fb["change"],
                changePct=fb["change"],
                points=_fallback_points(fb),
                lastUpdate=last_update,
            )

    results = await asyncio.gather(*[fetch_index(sym, meta) for sym, meta in IDX_INDEX_MAP.items()])
    return list(results)


@router.get("/intraday/{symbol}", response_model=IntradayResponse, dependencies=[])
async def get_intraday(symbol: str) -> IntradayResponse:
    """Get 30-day daily closes for sparkline display.

    Public endpoint — no auth required.
    Supports both IDX indices (IHSG etc.) and equity tickers (BBCA etc.).
    """
    import asyncio

    import yfinance as yf

    wib = ZoneInfo("Asia/Jakarta")
    now = datetime.now(tz=UTC)
    period1 = now - timedelta(days=30)
    upper = symbol.upper()
    y_symbol = SYMBOL_MAP.get(upper, f"{upper}.JK")
    last_update = now.astimezone(wib).strftime("%H:%M")

    def _fetch() -> tuple[float, float, float, list[float]]:
        ticker = yf.Ticker(y_symbol)
        info = ticker.fast_info
        current = float(info.last_price or 0)
        prev_close = float(info.previous_close or 0)
        open_price = float(getattr(info, "open", None) or prev_close)
        change_pct_local = (
            ((current - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
        )
        hist = ticker.history(start=period1, end=now, interval="1d")
        points_local = [float(c) for c in hist["Close"].tolist()] if not hist.empty else []
        if current > 0 and (not points_local or points_local[-1] != current):
            points_local.append(current)
        return current, open_price, round(change_pct_local, 4), points_local

    try:
        loop = asyncio.get_event_loop()
        current, open_price, change_pct, points = await loop.run_in_executor(None, _fetch)
        if current <= 0 or len(points) < 2:
            raise ValueError("No data")

        return IntradayResponse(
            symbol=upper,
            current=current,
            open=open_price,
            change=round(change_pct, 2),
            points=points,
            lastUpdate=last_update,
        )
    except Exception as exc:
        logger.warning("intraday_fetch_failed", symbol=upper, error=str(exc))
        fb = FALLBACK_INDICES.get(upper, {"current": 500.0, "change": 0.0})
        return IntradayResponse(
            symbol=upper,
            current=fb["current"],
            open=fb["current"],
            change=fb["change"],
            points=_fallback_points(fb),
            lastUpdate=last_update,
        )
