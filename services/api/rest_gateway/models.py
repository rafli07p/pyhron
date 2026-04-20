"""Request/response Pydantic models for the Pyhron REST gateway."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from services.api.rest_gateway.rbac import Role
from shared.schemas.order_events import (
    CancelReason,
    OrderSide,
    OrderStatusEnum,
    OrderType,
    TimeInForce,
)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class MarketDataRequest(BaseModel):
    interval: str = "1min"
    limit: int = Field(default=100, ge=1, le=5000)
    start: datetime | None = None
    end: datetime | None = None


class MarketDataResponse(BaseModel):
    symbol: str
    bars: list[dict[str, Any]] = Field(default_factory=list)
    quotes: list[dict[str, Any]] = Field(default_factory=list)


class CreateOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: OrderSide
    qty: Decimal = Field(..., gt=0)
    order_type: OrderType = OrderType.LIMIT
    price: Decimal | None = None
    stop_price: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.DAY
    strategy_id: str | None = None
    account_id: str | None = None


class CreateOrderResponse(BaseModel):
    order_id: UUID
    status: OrderStatusEnum = OrderStatusEnum.PENDING
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class CancelOrderRequest(BaseModel):
    order_id: UUID
    reason: CancelReason = CancelReason.USER_REQUESTED


class PositionResponse(BaseModel):
    symbol: str
    qty: Decimal
    avg_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


class PortfolioPnlResponse(BaseModel):
    tenant_id: str
    total_equity: Decimal
    total_pnl: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    positions: list[PositionResponse] = Field(default_factory=list)
    as_of: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class BacktestRequest(BaseModel):
    strategy_id: str
    symbols: list[str]
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal("1000000")
    parameters: dict[str, Any] = Field(default_factory=dict)


class BacktestResponse(BaseModel):
    backtest_id: UUID = Field(default_factory=uuid4)
    status: str = "submitted"
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class RiskCheckRequest(BaseModel):
    symbol: str
    side: OrderSide
    qty: Decimal
    price: Decimal | None = None
    account_id: str | None = None


class RiskCheckResponse(BaseModel):
    approved: bool
    checks: list[dict[str, Any]] = Field(default_factory=list)
    reason: str | None = None


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str
    role: Role = Role.VIEWER


class UserResponse(BaseModel):
    user_id: UUID = Field(default_factory=uuid4)
    username: str
    email: str
    role: Role
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class UserUpdateRequest(BaseModel):
    email: str | None = None
    role: Role | None = None
