"""Trading ORM models.

Tables:
  - orders: Persistent order state (mirrors Kafka event log)
  - positions: Current position state per strategy per symbol
  - trades: Immutable fill records (TimescaleDB hypertable)
  - risk_limits: Per-strategy risk parameters
"""

from __future__ import annotations

import warnings

warnings.warn(
    "data_platform.models.trading is deprecated. Use data_platform.database_models instead.",
    DeprecationWarning,
    stacklevel=2,
)

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base

if TYPE_CHECKING:
    from datetime import datetime

# ── Enums (match proto/orders.proto) ────────────────────────────────────────


class OrderSideEnum(enum.StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderTypeEnum(enum.StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForceEnum(enum.StrEnum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


class OrderStatusEnum(enum.StrEnum):
    PENDING_RISK = "pending_risk"
    RISK_APPROVED = "risk_approved"
    RISK_REJECTED = "risk_rejected"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ── Order ───────────────────────────────────────────────────────────────────


class Order(Base):
    """Persistent order state (source of truth alongside Kafka events)."""

    __tablename__ = "orders"

    client_order_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(100))
    strategy_id: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(10))
    side: Mapped[OrderSideEnum] = mapped_column(
        ENUM(OrderSideEnum, name="order_side_enum", create_type=False), nullable=False
    )
    order_type: Mapped[OrderTypeEnum] = mapped_column(
        ENUM(OrderTypeEnum, name="order_type_enum", create_type=False), nullable=False
    )
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    filled_quantity: Mapped[int] = mapped_column(BigInteger, default=0)
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    avg_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    status: Mapped[OrderStatusEnum] = mapped_column(
        ENUM(OrderStatusEnum, name="order_status_enum", create_type=False),
        nullable=False,
        default=OrderStatusEnum.PENDING_RISK,
    )
    currency: Mapped[str | None] = mapped_column(String(3))
    time_in_force: Mapped[TimeInForceEnum | None] = mapped_column(
        ENUM(TimeInForceEnum, name="time_in_force_enum", create_type=False)
    )
    commission: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    tax: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))

    signal_time: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    filled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        Index("ix_orders_strategy_created", "strategy_id", created_at.desc()),
        Index("ix_orders_symbol_status", "symbol", "status"),
        Index("ix_orders_broker_id", "broker_order_id"),
    )


# ── Position ────────────────────────────────────────────────────────────────


class Position(Base):
    """Current position state per strategy per symbol."""

    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(10))
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    avg_entry_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    last_updated: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (UniqueConstraint("strategy_id", "symbol", "exchange"),)


# ── Trade ───────────────────────────────────────────────────────────────────


class Trade(Base):
    """Immutable fill record. TimescaleDB hypertable on trade_time."""

    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    broker_trade_id: Mapped[str | None] = mapped_column(String(100))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(10))
    side: Mapped[OrderSideEnum] = mapped_column(
        ENUM(OrderSideEnum, name="order_side_enum", create_type=False), nullable=False
    )
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    commission: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    tax: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    trade_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        Index("ix_trades_order_id", "client_order_id"),
        Index("ix_trades_symbol_time", "symbol", trade_time.desc()),
    )


# ── RiskLimit ───────────────────────────────────────────────────────────────


class RiskLimit(Base):
    """Per-strategy risk parameters."""

    __tablename__ = "risk_limits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    max_position_size_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.10"))
    max_sector_concentration_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.30"))
    daily_loss_limit_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.02"))
    max_gross_exposure_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1.00"))
    max_var_95_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.05"))
    max_orders_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
