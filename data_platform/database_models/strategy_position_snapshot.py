"""Strategy position snapshot model.

Tracks the current position state per strategy per symbol, including
unrealised and realised PnL.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


class StrategyPositionSnapshot(Base):
    """Current position state per strategy per symbol.

    Attributes:
        id: Primary key (UUID).
        strategy_id: Strategy identifier.
        symbol: Ticker symbol.
        exchange: Exchange mic code.
        quantity: Net position quantity in shares.
        avg_entry_price: Volume-weighted average entry price.
        current_price: Most recent market price.
        unrealized_pnl: Mark-to-market unrealised profit/loss.
        realized_pnl: Cumulative realised profit/loss.
        market_value: Current market value of the position.
        last_updated: Timestamp of the most recent update.
    """

    __tablename__ = "strategy_position_snapshots"

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

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_positions_quantity_non_negative"),
        UniqueConstraint("strategy_id", "symbol", "exchange"),
    )
