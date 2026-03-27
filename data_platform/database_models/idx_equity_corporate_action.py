"""IDX equity corporate action events.

Tracks dividends, stock splits, reverse splits, and rights issues for
IDX-listed equities.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.async_database_session import Base


class ActionType(enum.StrEnum):
    """Corporate action type."""

    CASH_DIVIDEND = "cash_dividend"
    STOCK_DIVIDEND = "stock_dividend"
    SPLIT = "split"
    REVERSE_SPLIT = "reverse_split"
    RIGHTS = "rights"


class IdxEquityCorporateAction(Base):
    """Corporate action event for an IDX equity.

    Attributes:
        id: Primary key (UUID).
        symbol: Ticker symbol (FK to instruments).
        action_type: Type of corporate action.
        ex_date: Ex-date for the action.
        record_date: Record date.
        payment_date: Payment or distribution date.
        amount: Cash amount per share (if applicable).
        ratio: Split or stock dividend ratio (if applicable).
        currency: Currency ISO code.
        notes: Free-text notes.
        created_at: Row creation timestamp.
    """

    __tablename__ = "corporate_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("instruments.symbol"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType, name="action_type_enum"), nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    record_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    instrument = relationship("IdxEquityInstrument", back_populates="corporate_actions", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("symbol", "action_type", "ex_date"),
        Index(
            "ix_idx_equity_corporate_actions_symbol_ex_date",
            "symbol",
            ex_date.desc(),
        ),
    )
