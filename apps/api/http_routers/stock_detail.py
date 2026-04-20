"""IDX equity stock detail API endpoints.

Single stock deep dive: profile, financials, corporate actions,
and ownership structure.
"""

import asyncio
from datetime import date
from decimal import Decimal
from functools import partial
from typing import Any

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from data_platform.database_models.idx_equity_instrument import IdxEquityInstrument
from shared.async_database_session import get_session
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

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
# NOTE: `/` must be registered before `/{symbol}` so FastAPI matches it first.
@router.get("/", response_model=list[dict[str, str]])
async def list_symbols(
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[dict[str, str]]:
    """List all active IDX instruments for dropdown."""
    async with get_session() as session:
        result = await session.execute(
            select(IdxEquityInstrument.symbol, IdxEquityInstrument.company_name)
            .where(IdxEquityInstrument.is_active.is_(True))
            .order_by(IdxEquityInstrument.symbol)
        )
        rows = result.all()
    return [{"symbol": r.symbol, "name": r.company_name} for r in rows]


@router.get("/{symbol}", response_model=StockProfile)
async def get_stock_profile(
    symbol: str,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> StockProfile:
    """Get stock profile enriched with yfinance data."""
    logger.info("stock_profile_queried", symbol=symbol)

    async with get_session() as session:
        result = await session.execute(
            select(IdxEquityInstrument).where(
                IdxEquityInstrument.symbol == symbol.upper(),
                IdxEquityInstrument.is_active.is_(True),
            )
        )
        instrument = result.scalar_one_or_none()

    if instrument is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {symbol} not found",
        )

    def _fetch_yf(sym: str) -> dict[str, Any]:
        try:
            ticker = yf.Ticker(f"{sym}.JK")
            info = ticker.info or {}
            hist = ticker.history(period="2d")
            last_price = float(hist["Close"].iloc[-1]) if not hist.empty else None
            return {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "description": info.get("longBusinessSummary"),
                "market_cap": info.get("marketCap"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "last_price": last_price,
            }
        except Exception:
            return {}

    loop = asyncio.get_event_loop()
    yf_data = await loop.run_in_executor(None, partial(_fetch_yf, symbol.upper()))

    return StockProfile(
        symbol=instrument.symbol,
        name=instrument.company_name,
        exchange="IDX",
        sector=yf_data.get("sector") or instrument.sector,
        industry=yf_data.get("industry"),
        listing_date=instrument.listing_date,
        market_cap=(
            Decimal(str(yf_data["market_cap"]))
            if yf_data.get("market_cap")
            else (Decimal(instrument.market_cap_idr) if instrument.market_cap_idr else None)
        ),
        last_price=(
            Decimal(str(yf_data["last_price"])) if yf_data.get("last_price") else None
        ),
        shares_outstanding=yf_data.get("shares_outstanding") or instrument.shares_outstanding,
        is_lq45=False,
        description=yf_data.get("description"),
    )


@router.get("/{symbol}/financials", response_model=list[FinancialSummary])
async def get_financials(
    symbol: str,
    period_type: str = Query("annual", pattern="^(annual|quarterly)$"),
    limit: int = Query(8, ge=1, le=20),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[FinancialSummary]:
    """Get historical financial statements for a stock."""
    logger.info("financials_queried", symbol=symbol, period_type=period_type)
    return []


@router.get("/{symbol}/corporate-actions", response_model=list[CorporateAction])
async def get_corporate_actions(
    symbol: str,
    action_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[CorporateAction]:
    """Get corporate actions history (dividends, splits, rights issues)."""
    return []


@router.get("/{symbol}/ownership", response_model=list[OwnershipEntry])
async def get_ownership(symbol: str, _user: TokenPayload = Depends(require_role(Role.VIEWER))) -> list[OwnershipEntry]:
    """Get ownership breakdown for a stock."""
    return []
