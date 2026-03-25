"""Market event schemas for the Pyhron trading platform.

Defines Pydantic v2 models for all market data events including ticks,
OHLCV bars, trades, and quotes. All models enforce multi-tenancy via
mandatory ``tenant_id`` fields.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from datetime import datetime


class Exchange(StrEnum):
    """Supported exchanges."""

    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    CME = "CME"
    CBOE = "CBOE"
    ICE = "ICE"
    LSE = "LSE"
    TSE = "TSE"
    HKEX = "HKEX"
    SGX = "SGX"
    BATS = "BATS"
    IEX = "IEX"
    ARCA = "ARCA"
    OTHER = "OTHER"


class MarketEventBase(BaseModel):
    """Base class for all market events.

    Every market event carries a symbol, timestamp, exchange reference,
    and tenant identifier to support multi-tenant deployments.
    """

    model_config = {"frozen": True, "str_strip_whitespace": True}

    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    symbol: str = Field(..., min_length=1, max_length=20, description="Instrument symbol (e.g. AAPL, ESH5)")
    timestamp: datetime = Field(..., description="Event timestamp in UTC")
    exchange: Exchange = Field(default=Exchange.OTHER, description="Source exchange")
    tenant_id: str = Field(..., min_length=1, max_length=64, description="Tenant identifier for multi-tenancy")
    sequence_number: int | None = Field(default=None, ge=0, description="Exchange sequence number for ordering")


class TickEvent(MarketEventBase):
    """Single price tick from the market data feed.

    Represents the most granular price update: a single price/volume
    observation at a specific point in time.
    """

    price: Decimal = Field(..., gt=0, decimal_places=8, description="Tick price")
    volume: Decimal = Field(default=Decimal("0"), ge=0, description="Volume at this tick")
    condition: str | None = Field(default=None, max_length=16, description="Trade condition code")


class BarEvent(MarketEventBase):
    """OHLCV bar aggregated over a time interval.

    Represents a candlestick bar with open/high/low/close prices and
    total volume for the period.
    """

    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="Period high price")
    low: Decimal = Field(..., gt=0, description="Period low price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: Decimal = Field(default=Decimal("0"), ge=0, description="Total volume in the period")
    vwap: Decimal | None = Field(default=None, gt=0, description="Volume-weighted average price")
    bar_count: int | None = Field(default=None, ge=0, description="Number of ticks in the bar")
    interval_seconds: int = Field(default=60, gt=0, description="Bar interval in seconds")

    @model_validator(mode="after")
    def _validate_ohlc(self) -> BarEvent:
        """Ensure high >= low and high/low bracket open/close."""
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) must be >= low ({self.low})")
        if self.high < self.open or self.high < self.close:
            raise ValueError("high must be >= open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("low must be <= open and close")
        return self


class TradeEvent(MarketEventBase):
    """Individual trade execution reported by an exchange.

    Carries price, size, and optional aggressor side for trade-level
    analytics and VWAP calculations.
    """

    price: Decimal = Field(..., gt=0, description="Trade price")
    volume: Decimal = Field(..., gt=0, description="Trade size / quantity")
    aggressor_side: str | None = Field(
        default=None,
        pattern=r"^(BUY|SELL|UNKNOWN)$",
        description="Aggressor side of the trade",
    )
    trade_id: str | None = Field(default=None, max_length=64, description="Exchange-assigned trade ID")


class QuoteEvent(MarketEventBase):
    """Top-of-book quote update (best bid/ask).

    Represents the current best bid and ask with their respective sizes.
    Includes derived spread for convenience.
    """

    bid: Decimal = Field(..., ge=0, description="Best bid price")
    ask: Decimal = Field(..., ge=0, description="Best ask price")
    bid_size: Decimal = Field(default=Decimal("0"), ge=0, description="Size at best bid")
    ask_size: Decimal = Field(default=Decimal("0"), ge=0, description="Size at best ask")
    mid: Decimal | None = Field(default=None, description="Mid price (computed if not provided)")
    spread: Decimal | None = Field(default=None, description="Bid-ask spread (computed if not provided)")

    @model_validator(mode="after")
    def _compute_derived_fields(self) -> QuoteEvent:
        """Compute mid and spread if not explicitly provided."""
        obj = self
        if obj.bid > 0 and obj.ask > 0:
            if obj.mid is None:
                object.__setattr__(obj, "mid", (obj.bid + obj.ask) / 2)
            if obj.spread is None:
                object.__setattr__(obj, "spread", obj.ask - obj.bid)
        return obj

    @model_validator(mode="after")
    def _validate_bid_ask(self) -> QuoteEvent:
        """Bid must not exceed ask when both are positive."""
        if self.bid > 0 and self.ask > 0 and self.bid > self.ask:
            raise ValueError(f"bid ({self.bid}) must be <= ask ({self.ask})")
        return self


__all__ = [
    "BarEvent",
    "Exchange",
    "MarketEventBase",
    "QuoteEvent",
    "TickEvent",
    "TradeEvent",
]
