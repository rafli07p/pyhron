"""IDX equity index constituent membership.

Tracks which equities belong to major IDX indices (LQ45, IDX30, IDX80)
over time, including effective/removal dates and portfolio weights.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class IdxEquityIndexConstituent(Base):
    """Index constituent membership record.

    Attributes:
        id: Primary key (UUID).
        index_name: Index identifier (e.g. ``"LQ45"``, ``"IDX30"``, ``"IDX80"``).
        symbol: Ticker symbol (FK to instruments).
        effective_date: Date the constituent was added to the index.
        removal_date: Date the constituent was removed (null if still active).
        weight_pct: Portfolio weight as a percentage.
        created_at: Row creation timestamp.
    """

    __tablename__ = "index_constituents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    index_name: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("instruments.symbol"),
        nullable=False,
        index=True,
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    removal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("index_name", "symbol", "effective_date"),
        Index(
            "ix_idx_equity_index_constituents_index_name",
            "index_name",
        ),
    )
