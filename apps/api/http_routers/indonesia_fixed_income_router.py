"""Indonesia fixed income API endpoints.

Government bonds (SBN/SUN), corporate bonds, yield curves,
and credit spread analysis for the Indonesian bond market.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/fixed-income", tags=["fixed-income"])


# Response Models
class GovernmentBond(BaseModel):
    series: str = Field(description="e.g. FR0098, FR0100, PBS035")
    bond_type: str = Field(description="SUN, SBSN, SPN")
    coupon_rate: Decimal
    maturity_date: date
    yield_to_maturity: float
    price: Decimal
    duration: float | None = None
    outstanding: Decimal | None = None


class CorporateBond(BaseModel):
    series: str
    issuer: str
    issuer_symbol: str | None = None
    rating: str = Field(description="e.g. AAA, AA+, AA, A")
    coupon_rate: Decimal
    maturity_date: date
    yield_to_maturity: float
    price: Decimal


class YieldCurvePoint(BaseModel):
    tenor: str
    yield_pct: float
    change_bps: float | None = None


class CreditSpread(BaseModel):
    rating: str
    tenor: str
    spread_bps: float
    change_bps: float | None = None
    benchmark_yield: float


# Endpoints
@router.get("/government-bonds", response_model=list[GovernmentBond])
async def get_government_bonds(
    bond_type: str | None = Query(None, description="SUN, SBSN, SPN"),
    min_tenor_years: int | None = Query(None, ge=0),
    max_tenor_years: int | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[GovernmentBond]:
    """Get Indonesian government bond listings with yield data."""
    logger.info("govt_bonds_queried", bond_type=bond_type)
    return []


@router.get("/corporate-bonds", response_model=list[CorporateBond])
async def get_corporate_bonds(
    rating: str | None = Query(None, description="Credit rating filter"),
    issuer_symbol: str | None = Query(None, description="Filter by issuer stock symbol"),
    limit: int = Query(50, ge=1, le=200),
) -> list[CorporateBond]:
    """Get corporate bond listings with yield and rating data."""
    return []


@router.get("/yield-curve", response_model=list[YieldCurvePoint])
async def get_yield_curve(
    curve_date: date | None = Query(None),
    bond_type: str = Query("SUN", description="SUN or SBSN"),
) -> list[YieldCurvePoint]:
    """Get government bond yield curve for a specific date."""
    return []


@router.get("/credit-spreads", response_model=list[CreditSpread])
async def get_credit_spreads(
    rating: str | None = Query(None),
) -> list[CreditSpread]:
    """Get credit spreads by rating and tenor over government benchmark."""
    return []
