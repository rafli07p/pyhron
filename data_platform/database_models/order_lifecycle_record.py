"""Order lifecycle record model.

Persists the full order state machine alongside Kafka event log,
serving as the source of truth for order management.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Index, Numeric, String
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class OrderSideEnum(enum.StrEnum):
    """Order side."""

    BUY = "buy"
    SELL = "sell"


class OrderTypeEnum(enum.StrEnum):
    """Order type."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForceEnum(enum.StrEnum):
    """Time-in-force policy."""

    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


class OrderStatusEnum(enum.StrEnum):
    """Order status."""

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


class OrderLifecycleRecord(Base):
    """Persistent order state (source of truth alongside Kafka events).

    Attributes:
        client_order_id: Client-generated order identifier (primary key).
        broker_order_id: Broker-assigned order identifier.
        strategy_id: Strategy that originated the order.
        symbol: Ticker symbol.
        exchange: Exchange mic code.
        side: Buy or sell.
        order_type: Market, limit, stop, or stop-limit.
        quantity: Ordered quantity in shares.
        filled_quantity: Cumulative filled quantity.
        limit_price: Limit price (for limit/stop-limit orders).
        stop_price: Stop trigger price.
        avg_fill_price: Volume-weighted average fill price.
        status: Current order status.
        currency: Order currency ISO code.
        time_in_force: Time-in-force policy.
        commission: Broker commission in currency units.
        tax: Transaction tax in currency units.
        signal_time: Timestamp of the originating signal.
        submitted_at: Timestamp when submitted to the broker.
        acknowledged_at: Timestamp of broker acknowledgement.
        filled_at: Timestamp of final fill.
        created_at: Row creation timestamp.
        updated_at: Row last-update timestamp.
    """

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
        CheckConstraint("filled_quantity <= quantity", name="ck_orders_filled_lte_quantity"),
        Index(
            "ix_order_lifecycle_records_strategy_created",
            "strategy_id",
            created_at.desc(),
        ),
        Index("ix_order_lifecycle_records_symbol_status", "symbol", "status"),
        Index("ix_order_lifecycle_records_broker_id", "broker_order_id"),
    )
