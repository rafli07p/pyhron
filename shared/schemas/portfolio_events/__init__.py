"""Portfolio event schemas for the Enthropy trading platform.

Defines Pydantic v2 models for position tracking, P&L reporting, and
risk exposure updates.  All models enforce multi-tenancy via mandatory
``tenant_id`` fields.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AssetClass(StrEnum):
    """Broad asset class categories."""

    EQUITY = "EQUITY"
    FIXED_INCOME = "FIXED_INCOME"
    FX = "FX"
    COMMODITY = "COMMODITY"
    CRYPTO = "CRYPTO"
    DERIVATIVE = "DERIVATIVE"
    OTHER = "OTHER"


class ExposureType(StrEnum):
    """Types of risk exposure."""

    GROSS = "GROSS"
    NET = "NET"
    LONG = "LONG"
    SHORT = "SHORT"
    DELTA = "DELTA"
    GAMMA = "GAMMA"
    VEGA = "VEGA"
    BETA = "BETA"
    SECTOR = "SECTOR"
    COUNTRY = "COUNTRY"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class PortfolioEventBase(BaseModel):
    """Base class for all portfolio events."""

    model_config = {"frozen": True, "str_strip_whitespace": True}

    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    portfolio_id: str = Field(..., min_length=1, max_length=64, description="Portfolio / book identifier")
    tenant_id: str = Field(..., min_length=1, max_length=64, description="Tenant identifier for multi-tenancy")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp (UTC)")


class PositionUpdate(PortfolioEventBase):
    """Real-time position snapshot for a single instrument.

    Published whenever a fill changes the portfolio's holdings in
    a given symbol.
    """

    symbol: str = Field(..., min_length=1, max_length=20, description="Instrument symbol")
    quantity: Decimal = Field(..., description="Signed position quantity (negative = short)")
    avg_cost: Decimal = Field(default=Decimal("0"), description="Average cost basis per unit")
    market_price: Decimal = Field(default=Decimal("0"), ge=0, description="Latest market price")
    market_value: Decimal = Field(default=Decimal("0"), description="Current market value (qty * market_price)")
    unrealized_pnl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L vs. cost basis")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L from closed lots")
    asset_class: AssetClass = Field(default=AssetClass.EQUITY, description="Asset class of the instrument")
    currency: str = Field(default="USD", max_length=3, description="Position currency (ISO 4217)")

    @model_validator(mode="after")
    def _validate_market_value(self) -> "PositionUpdate":
        """Market value should be consistent with quantity * market_price."""
        expected = self.quantity * self.market_price
        if self.market_value != Decimal("0") and self.market_price != Decimal("0"):
            tolerance = abs(expected) * Decimal("0.001")
            if abs(self.market_value - expected) > max(tolerance, Decimal("0.01")):
                raise ValueError(
                    f"market_value ({self.market_value}) is inconsistent with "
                    f"quantity * market_price ({expected})"
                )
        return self


class PnLUpdate(PortfolioEventBase):
    """Aggregate P&L update for a portfolio or sub-book.

    Published periodically (e.g. every second) and on every fill to
    give traders a real-time view of their P&L.
    """

    symbol: Optional[str] = Field(default=None, max_length=20, description="Symbol (None = portfolio-level)")
    unrealized_pnl: Decimal = Field(default=Decimal("0"), description="Total unrealized P&L")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Total realized P&L")
    total_pnl: Decimal = Field(default=Decimal("0"), description="Unrealized + realized P&L")
    daily_pnl: Decimal = Field(default=Decimal("0"), description="P&L since start of trading day")
    mtd_pnl: Decimal = Field(default=Decimal("0"), description="Month-to-date P&L")
    ytd_pnl: Decimal = Field(default=Decimal("0"), description="Year-to-date P&L")
    market_value: Decimal = Field(default=Decimal("0"), description="Aggregate market value")
    currency: str = Field(default="USD", max_length=3, description="Reporting currency (ISO 4217)")

    @model_validator(mode="after")
    def _validate_total_pnl(self) -> "PnLUpdate":
        expected = self.unrealized_pnl + self.realized_pnl
        if self.total_pnl != Decimal("0"):
            if abs(self.total_pnl - expected) > Decimal("0.01"):
                raise ValueError(
                    f"total_pnl ({self.total_pnl}) must equal "
                    f"unrealized_pnl + realized_pnl ({expected})"
                )
        return self


class ExposureUpdate(PortfolioEventBase):
    """Risk exposure snapshot for a portfolio.

    Captures various risk dimensions (gross, net, Greeks, sector,
    country) at a point in time for risk monitoring dashboards.
    """

    exposure_type: ExposureType = Field(..., description="Type of exposure being reported")
    symbol: Optional[str] = Field(default=None, max_length=20, description="Symbol (None = portfolio-level)")
    quantity: Decimal = Field(default=Decimal("0"), description="Exposure in units / contracts")
    market_value: Decimal = Field(default=Decimal("0"), description="Exposure in monetary terms")
    notional_value: Decimal = Field(default=Decimal("0"), description="Notional exposure value")
    weight_pct: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("-100"),
        le=Decimal("100"),
        description="Weight as percentage of total portfolio",
    )
    limit_value: Optional[Decimal] = Field(default=None, ge=0, description="Risk limit for this exposure type")
    utilization_pct: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Limit utilization (market_value / limit_value * 100)",
    )
    breach: bool = Field(default=False, description="True if exposure exceeds the defined limit")
    currency: str = Field(default="USD", max_length=3, description="Reporting currency (ISO 4217)")
    asset_class: Optional[AssetClass] = Field(default=None, description="Asset class filter")
    sector: Optional[str] = Field(default=None, max_length=64, description="GICS sector (for sector exposure)")
    country: Optional[str] = Field(default=None, max_length=3, description="ISO 3166-1 alpha-3 country code")


__all__ = [
    "AssetClass",
    "ExposureType",
    "PortfolioEventBase",
    "PositionUpdate",
    "PnLUpdate",
    "ExposureUpdate",
]
