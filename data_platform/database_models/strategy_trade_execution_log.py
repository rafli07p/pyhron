"""Strategy trade execution log model.

Stores immutable fill records for all trade executions, designed as a
TimescaleDB hypertable partitioned on trade_time.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Index, Numeric, String
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class TradeSideEnum(enum.StrEnum):
    """Trade side."""

    BUY = "buy"
    SELL = "sell"


class StrategyTradeExecutionLog(Base):
    """Immutable fill record. TimescaleDB hypertable on ``trade_time``.

    Attributes:
        id: Primary key (UUID).
        client_order_id: Client order identifier linking to the originating order.
        broker_trade_id: Broker-assigned trade identifier.
        symbol: Ticker symbol.
        exchange: Exchange mic code.
        side: Buy or sell.
        quantity: Filled quantity in shares.
        price: Execution price.
        commission: Broker commission.
        tax: Transaction tax.
        trade_time: Timestamp of the fill.
        created_at: Row creation timestamp.
    """

    __tablename__ = "trade_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_order_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    broker_trade_id: Mapped[str | None] = mapped_column(String(100))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(10))
    side: Mapped[TradeSideEnum] = mapped_column(
        ENUM(TradeSideEnum, name="trade_side_enum", create_type=False), nullable=False
    )
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    commission: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    tax: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    trade_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        Index(
            "ix_strategy_trade_execution_logs_order_id",
            "client_order_id",
        ),
        Index(
            "ix_strategy_trade_execution_logs_symbol_time",
            "symbol",
            trade_time.desc(),
        ),
    )
