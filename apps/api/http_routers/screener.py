"""IDX equity screener API endpoints.

Advanced multi-factor stock screening for the Indonesia Stock Exchange
with fundamental and technical filters.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select

from data_platform.database_models.idx_equity_computed_ratio import IdxEquityComputedRatio
from data_platform.database_models.idx_equity_index_constituent import IdxEquityIndexConstituent
from data_platform.database_models.idx_equity_instrument import IdxEquityInstrument
from data_platform.database_models.idx_equity_ohlcv_tick import IdxEquityOhlcvTick
from shared.async_database_session import get_session
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/screener", tags=["screener"])


# Response Models
class ScreenerResult(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    last_price: Decimal
    change_pct: float
    volume: int
    market_cap: Decimal | None = None
    pe_ratio: float | None = None
    pbv_ratio: float | None = None
    roe: float | None = None
    dividend_yield: float | None = None
    is_lq45: bool = False


class ScreenerMeta(BaseModel):
    total_matches: int
    filters_applied: dict[str, str] = Field(default_factory=dict)
    sort_by: str
    limit: int


class ScreenerResponse(BaseModel):
    meta: ScreenerMeta
    results: list[ScreenerResult]


# Endpoints
@router.get("/screen", response_model=ScreenerResponse)
async def screen_stocks(
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
    sector: str | None = Query(None, description="IDX sector code"),
    market_cap_min: Decimal | None = Query(None, description="Min market cap in IDR"),
    market_cap_max: Decimal | None = Query(None, description="Max market cap in IDR"),
    pe_min: float | None = Query(None, description="Min P/E ratio"),
    pe_max: float | None = Query(None, description="Max P/E ratio"),
    pbv_min: float | None = Query(None, description="Min P/BV ratio"),
    pbv_max: float | None = Query(None, description="Max P/BV ratio"),
    roe_min: float | None = Query(None, ge=0, description="Min ROE percentage"),
    dividend_yield_min: float | None = Query(None, ge=0, description="Min dividend yield"),
    lq45_only: bool = Query(False, description="Filter to LQ45 constituents only"),
    sort_by: str = Query(
        "market_cap",
        pattern="^(market_cap|pe_ratio|pbv_ratio|roe|dividend_yield|change_pct|volume)$",
    ),
    limit: int = Query(50, ge=1, le=200),
) -> ScreenerResponse:
    """Screen IDX equities using multi-factor fundamental filters."""
    filters = {
        k: str(v)
        for k, v in {
            "sector": sector,
            "market_cap_min": market_cap_min,
            "market_cap_max": market_cap_max,
            "pe_min": pe_min,
            "pe_max": pe_max,
            "pbv_min": pbv_min,
            "pbv_max": pbv_max,
            "roe_min": roe_min,
            "dividend_yield_min": dividend_yield_min,
            "lq45_only": lq45_only if lq45_only else None,
        }.items()
        if v is not None
    }
    logger.info("screener_query", filters=filters, sort_by=sort_by, limit=limit)

    async with get_session() as session:
        # Subquery: latest computed_ratios per symbol
        latest_ratio_date = (
            select(
                IdxEquityComputedRatio.symbol,
                func.max(IdxEquityComputedRatio.date).label("max_date"),
            )
            .group_by(IdxEquityComputedRatio.symbol)
            .subquery("latest_ratio_date")
        )

        # Subquery: latest OHLCV per symbol (for last_price)
        latest_ohlcv_time = (
            select(
                IdxEquityOhlcvTick.symbol,
                func.max(IdxEquityOhlcvTick.time).label("max_time"),
            )
            .group_by(IdxEquityOhlcvTick.symbol)
            .subquery("latest_ohlcv_time")
        )

        # LQ45 membership subquery
        lq45_subq = (
            select(IdxEquityIndexConstituent.symbol)
            .where(
                IdxEquityIndexConstituent.index_name == "LQ45",
                IdxEquityIndexConstituent.removal_date.is_(None),
            )
            .subquery("lq45")
        )

        # Main query: instruments joined with latest ratios and latest ohlcv
        stmt = (
            select(
                IdxEquityInstrument.symbol,
                IdxEquityInstrument.company_name.label("name"),
                IdxEquityInstrument.sector,
                IdxEquityOhlcvTick.close.label("last_price"),
                IdxEquityOhlcvTick.volume,
                IdxEquityComputedRatio.market_cap_idr.label("market_cap"),
                IdxEquityComputedRatio.pe_ratio,
                IdxEquityComputedRatio.pb_ratio,
                IdxEquityComputedRatio.roe_pct,
                IdxEquityComputedRatio.dividend_yield_pct,
                lq45_subq.c.symbol.label("lq45_symbol"),
            )
            .select_from(IdxEquityInstrument)
            .outerjoin(
                latest_ratio_date,
                IdxEquityInstrument.symbol == latest_ratio_date.c.symbol,
            )
            .outerjoin(
                IdxEquityComputedRatio,
                and_(
                    IdxEquityComputedRatio.symbol == IdxEquityInstrument.symbol,
                    IdxEquityComputedRatio.date == latest_ratio_date.c.max_date,
                ),
            )
            .outerjoin(
                latest_ohlcv_time,
                IdxEquityInstrument.symbol == latest_ohlcv_time.c.symbol,
            )
            .outerjoin(
                IdxEquityOhlcvTick,
                and_(
                    IdxEquityOhlcvTick.symbol == IdxEquityInstrument.symbol,
                    IdxEquityOhlcvTick.time == latest_ohlcv_time.c.max_time,
                ),
            )
            .outerjoin(
                lq45_subq,
                IdxEquityInstrument.symbol == lq45_subq.c.symbol,
            )
            .where(IdxEquityInstrument.is_active.is_(True))
        )

        # Apply filters
        if sector is not None:
            stmt = stmt.where(IdxEquityInstrument.sector == sector)
        if pe_min is not None:
            stmt = stmt.where(IdxEquityComputedRatio.pe_ratio >= pe_min)
        if pe_max is not None:
            stmt = stmt.where(IdxEquityComputedRatio.pe_ratio <= pe_max)
        if pbv_min is not None:
            stmt = stmt.where(IdxEquityComputedRatio.pb_ratio >= pbv_min)
        if pbv_max is not None:
            stmt = stmt.where(IdxEquityComputedRatio.pb_ratio <= pbv_max)
        if roe_min is not None:
            stmt = stmt.where(IdxEquityComputedRatio.roe_pct >= roe_min)
        if dividend_yield_min is not None:
            stmt = stmt.where(IdxEquityComputedRatio.dividend_yield_pct >= dividend_yield_min)
        if market_cap_min is not None:
            stmt = stmt.where(IdxEquityComputedRatio.market_cap_idr >= int(market_cap_min))
        if market_cap_max is not None:
            stmt = stmt.where(IdxEquityComputedRatio.market_cap_idr <= int(market_cap_max))
        if lq45_only:
            stmt = stmt.where(lq45_subq.c.symbol.is_not(None))

        # Sorting
        sort_column_map = {
            "market_cap": IdxEquityComputedRatio.market_cap_idr,
            "pe_ratio": IdxEquityComputedRatio.pe_ratio,
            "pbv_ratio": IdxEquityComputedRatio.pb_ratio,
            "roe": IdxEquityComputedRatio.roe_pct,
            "dividend_yield": IdxEquityComputedRatio.dividend_yield_pct,
            "volume": IdxEquityOhlcvTick.volume,
            "change_pct": IdxEquityOhlcvTick.close,  # fallback sort by close
        }
        sort_col = sort_column_map.get(sort_by, IdxEquityComputedRatio.market_cap_idr)
        stmt = stmt.order_by(sort_col.desc().nullslast())

        # Get total count before applying limit
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await session.execute(count_stmt)
        total_matches = count_result.scalar_one()

        # Apply limit
        stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        rows = result.all()

    results = [
        ScreenerResult(
            symbol=row.symbol,
            name=row.name,
            sector=row.sector,
            last_price=row.last_price or Decimal("0"),
            change_pct=0.0,  # Would need previous close to compute
            volume=row.volume or 0,
            market_cap=Decimal(row.market_cap) if row.market_cap is not None else None,
            pe_ratio=float(row.pe_ratio) if row.pe_ratio is not None else None,
            pbv_ratio=float(row.pb_ratio) if row.pb_ratio is not None else None,
            roe=float(row.roe_pct) if row.roe_pct is not None else None,
            dividend_yield=float(row.dividend_yield_pct) if row.dividend_yield_pct is not None else None,
            is_lq45=row.lq45_symbol is not None,
        )
        for row in rows
    ]

    return ScreenerResponse(
        meta=ScreenerMeta(
            total_matches=total_matches,
            filters_applied=filters,
            sort_by=sort_by,
            limit=limit,
        ),
        results=results,
    )
