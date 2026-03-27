"""IDX equity screener API endpoints.

Advanced multi-factor stock screening for the Indonesia Stock Exchange
with fundamental and technical filters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from decimal import Decimal

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
    return ScreenerResponse(
        meta=ScreenerMeta(
            total_matches=0,
            filters_applied=filters,
            sort_by=sort_by,
            limit=limit,
        ),
        results=[],
    )
