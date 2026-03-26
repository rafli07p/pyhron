from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, computed_field, model_validator


class TickData(BaseModel):
    symbol: str
    price: Decimal = Field(ge=0)
    volume: int = Field(ge=0)
    bid: Decimal
    ask: Decimal
    timestamp: datetime
    exchange: str

    @model_validator(mode="after")
    def validate_no_crossed_market(self) -> TickData:
        if self.bid > self.ask:
            raise ValueError("bid must be <= ask (no crossed markets)")
        return self

    @computed_field
    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid
