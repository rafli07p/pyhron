"""Indonesia macro economic dashboard API endpoints.

Key macroeconomic indicators, yield curves, and Bank Indonesia
policy calendar for the Indonesian economy.
"""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/macro", tags=["macro-dashboard"])


# Response Models
class MacroIndicator(BaseModel):
    code: str = Field(description="e.g. GDP_GROWTH, CPI_YOY, BI_RATE")
    name: str
    latest_value: Decimal
    unit: str
    period: str
    source: str = "BPS/BI"
    updated_at: datetime


class IndicatorDataPoint(BaseModel):
    period: str
    value: Decimal
    date: date


class IndicatorHistory(BaseModel):
    code: str
    name: str
    unit: str
    data_points: list[IndicatorDataPoint]


class YieldCurvePoint(BaseModel):
    tenor: str = Field(description="e.g. 1M, 3M, 6M, 1Y, 5Y, 10Y, 30Y")
    yield_pct: float
    change_bps: float | None = None


class PolicyEvent(BaseModel):
    event_date: date
    event_type: str = Field(description="rate_decision, data_release, auction")
    title: str
    description: str | None = None
    previous_value: str | None = None
    consensus: str | None = None
    actual: str | None = None


# Endpoints
@router.get("/indicators", response_model=list[MacroIndicator])
async def get_indicators(
    category: str | None = Query(None, description="growth, inflation, monetary, trade"),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[MacroIndicator]:
    """Get latest values for all macro economic indicators."""
    logger.info("macro_indicators_queried", category=category)
    return []


@router.get("/indicators/{indicator_code}/history", response_model=IndicatorHistory)
async def get_indicator_history(
    indicator_code: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> IndicatorHistory:
    """Get historical data for a specific macro indicator."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Indicator {indicator_code} not found",
    )


@router.get("/yield-curve", response_model=list[YieldCurvePoint])
async def get_yield_curve(
    curve_date: date | None = Query(None, description="Date for yield curve snapshot"),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[YieldCurvePoint]:
    """Get Indonesian government bond yield curve."""
    return []


@router.get("/policy-calendar", response_model=list[PolicyEvent])
async def get_policy_calendar(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    event_type: str | None = Query(None),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[PolicyEvent]:
    """Get Bank Indonesia and BPS policy/data release calendar."""
    return []
