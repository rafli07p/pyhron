from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderCreate(BaseModel):
    symbol: str = Field(min_length=1)
    side: OrderSide
    order_type: OrderType
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = None
    strategy_id: str

    @model_validator(mode="after")
    def validate_price_required(self) -> OrderCreate:
        requires_price = {OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT}
        if self.order_type in requires_price and self.price is None:
            raise ValueError("price is required for limit, stop, and stop_limit orders")
        return self


class OrderResponse(BaseModel):
    order_id: UUID
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    filled_quantity: Decimal
    price: Decimal | None
    average_fill_price: Decimal | None
    status: OrderStatus
    strategy_id: str
    created_at: datetime
    updated_at: datetime
