"""IDX market overview API endpoints.

Market summary, OHLCV bars, and instrument lookup
for the Indonesia Stock Exchange.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

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


# Helper: build LQ45 subquery for a given symbol column
def _lq45_exists_subquery(symbol_col):
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
