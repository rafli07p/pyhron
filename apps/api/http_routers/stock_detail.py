"""IDX equity stock detail API endpoints.

Single stock deep dive: profile, financials, corporate actions,
and ownership structure.
"""

import asyncio
import contextlib
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
    """Get historical financial statements for a stock via yfinance."""
    logger.info("financials_queried", symbol=symbol, period_type=period_type)

    def _fetch(sym: str, ptype: str) -> list[dict[str, Any]]:
        try:
            t = yf.Ticker(f"{sym}.JK")
            fin = t.financials if ptype == "annual" else t.quarterly_financials
            if fin is None or fin.empty:
                return []
            info = t.info or {}

            def _safe(key: str, col: Any) -> float | None:
                try:
                    if key in fin.index:
                        v = fin.loc[key, col]
                        if v is None or str(v) == "nan":
                            return None
                        return float(v)
                except Exception:
                    return None
                return None

            results: list[dict[str, Any]] = []
            for col in list(fin.columns)[:limit]:
                try:
                    period_label = col.strftime("%Y") if ptype == "annual" else col.strftime("%Y-%m")
                except Exception:
                    period_label = str(col)[:7]
                results.append(
                    {
                        "symbol": sym,
                        "period": period_label,
                        "revenue": _safe("Total Revenue", col),
                        "net_income": _safe("Net Income", col),
                        "total_assets": None,
                        "total_equity": None,
                        "eps": _safe("Basic EPS", col),
                        "pe_ratio": info.get("trailingPE"),
                        "pbv_ratio": info.get("priceToBook"),
                        "roe": info.get("returnOnEquity"),
                        "der": info.get("debtToEquity"),
                    }
                )
            return results
        except Exception:
            logger.warning("financials_fetch_failed", symbol=sym)
            return []

    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, partial(_fetch, symbol.upper(), period_type))
    return [FinancialSummary(**r) for r in raw]


@router.get("/{symbol}/corporate-actions", response_model=list[CorporateAction])
async def get_corporate_actions(
    symbol: str,
    action_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[CorporateAction]:
    """Get corporate actions history (dividends, splits) via yfinance."""
    def _fetch(sym: str) -> list[dict[str, Any]]:
        try:
            t = yf.Ticker(f"{sym}.JK")
            results: list[dict[str, Any]] = []
            divs = t.dividends
            if divs is not None and not divs.empty:
                for ts, val in divs.tail(limit).items():
                    with contextlib.suppress(Exception):
                        results.append(
                            {
                                "symbol": sym,
                                "action_type": "dividend",
                                "ex_date": ts.date(),
                                "record_date": None,
                                "description": f"Cash Dividend IDR {val:,.0f} per share",
                                "value": float(val),
                            }
                        )
            splits = t.splits
            if splits is not None and not splits.empty:
                for ts, ratio in splits.tail(5).items():
                    with contextlib.suppress(Exception):
                        results.append(
                            {
                                "symbol": sym,
                                "action_type": "stock_split",
                                "ex_date": ts.date(),
                                "record_date": None,
                                "description": f"Stock Split {ratio}:1",
                                "value": float(ratio),
                            }
                        )
            results.sort(key=lambda x: x["ex_date"], reverse=True)
            return results[:limit]
        except Exception:
            logger.warning("corp_actions_fetch_failed", symbol=sym)
            return []

    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, partial(_fetch, symbol.upper()))
    if action_type:
        raw = [r for r in raw if r["action_type"] == action_type]
    return [CorporateAction(**r) for r in raw]


@router.get("/{symbol}/ownership", response_model=list[OwnershipEntry])
async def get_ownership(
    symbol: str,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[OwnershipEntry]:
    """Get ownership breakdown (insider/institutional/public) via yfinance."""
    def _fetch(sym: str) -> list[dict[str, Any]]:
        try:
            t = yf.Ticker(f"{sym}.JK")
            holders = t.major_holders
            if holders is None or holders.empty:
                return []

            def _safe_pct(key: str) -> float:
                try:
                    row = holders[holders.index == key]
                    if not row.empty:
                        return float(row.iloc[0, 0]) * 100
                except Exception:
                    return 0.0
                return 0.0

            insider_pct = _safe_pct("insidersPercentHeld")
            inst_pct = _safe_pct("institutionsPercentHeld")
            public_pct = max(0.0, 100.0 - insider_pct - inst_pct)

            results: list[dict[str, Any]] = []
            if insider_pct > 0:
                results.append({
                    "holder_name": "Insider / Management",
                    "holder_type": "insider",
                    "shares_held": 0,
                    "ownership_pct": round(insider_pct, 2),
                    "change_from_prior": None,
                })
            if inst_pct > 0:
                results.append({
                    "holder_name": "Institutional Investors",
                    "holder_type": "institution",
                    "shares_held": 0,
                    "ownership_pct": round(inst_pct, 2),
                    "change_from_prior": None,
                })
            if public_pct > 0:
                results.append({
                    "holder_name": "Public / Retail",
                    "holder_type": "public",
                    "shares_held": 0,
                    "ownership_pct": round(public_pct, 2),
                    "change_from_prior": None,
                })
            return results
        except Exception:
            logger.warning("ownership_fetch_failed", symbol=sym)
            return []

    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, partial(_fetch, symbol.upper()))
    return [OwnershipEntry(**r) for r in raw]


# IDX sector peers (static curated list; tier 1 LQ45 constituents)
SECTOR_PEERS: dict[str, list[str]] = {
    "BBCA": ["BBRI", "BMRI", "BBNI", "BNGA", "BDMN"],
    "BBRI": ["BBCA", "BMRI", "BBNI", "BNGA"],
    "BMRI": ["BBCA", "BBRI", "BBNI", "BNGA"],
    "BBNI": ["BBCA", "BBRI", "BMRI", "BNGA"],
    "TLKM": ["EXCL", "ISAT", "FREN"],
    "ASII": ["SMSM", "AUTO", "IMAS"],
    "UNVR": ["ICBP", "MYOR", "KLBF"],
    "GOTO": ["BUKA", "EMTK"],
}


@router.get("/{symbol}/peers", response_model=list[dict[str, Any]])
async def get_peers(
    symbol: str,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[dict[str, Any]]:
    """Get peer comparison — same sector stocks with key metrics."""
    upper = symbol.upper()
    peers = SECTOR_PEERS.get(upper, [])
    if not peers:
        async with get_session() as db:
            instr_res = await db.execute(
                select(IdxEquityInstrument.symbol)
                .where(IdxEquityInstrument.is_active.is_(True))
                .limit(6)
            )
            peers = [r[0] for r in instr_res.all() if r[0] != upper][:5]

    all_symbols = [upper, *peers[:5]]

    def _fetch_peers(syms: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for sym in syms:
            try:
                t = yf.Ticker(f"{sym}.JK")
                info = t.info or {}
                hist = t.history(period="2d")
                last_price_raw = float(hist["Close"].iloc[-1]) if not hist.empty else None
                # yfinance returns dividendYield as a decimal fraction (e.g. 0.0523 = 5.23%).
                # Fall back to trailingAnnualDividendYield when not present.
                raw_yield = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
                dividend_yield = round(float(raw_yield) * 100, 2) if raw_yield else None
                results.append({
                    "symbol": sym,
                    "name": info.get("shortName", sym),
                    "last_price": round(last_price_raw, 0) if last_price_raw else None,
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "pbv_ratio": info.get("priceToBook"),
                    "roe": info.get("returnOnEquity"),
                    "dividend_yield": dividend_yield,
                    "is_selected": sym == upper,
                })
            except Exception:
                results.append({
                    "symbol": sym,
                    "name": sym,
                    "last_price": None,
                    "market_cap": None,
                    "pe_ratio": None,
                    "pbv_ratio": None,
                    "roe": None,
                    "dividend_yield": None,
                    "is_selected": sym == upper,
                })
        return results

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_fetch_peers, all_symbols))
