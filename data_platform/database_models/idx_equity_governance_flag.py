"""IDX equity governance flags and events.

Tracks governance-relevant events such as ownership changes, audit opinions,
related-party transaction disclosures, and share pledges for ESG screening.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.async_database_session import Base


class IdxEquityGovernanceFlag(Base):
    """Governance flag or event for an IDX equity.

    Attributes:
        id: Primary key (UUID).
        symbol: Ticker symbol (FK to instruments).
        flag_type: Type of governance event (e.g. ``"OWNERSHIP_CHANGE"``).
        severity: Severity level (``"HIGH"``, ``"MEDIUM"``, ``"LOW"``).
        title: Short title or headline.
        description: Detailed description of the event.
        filer_name: Name of the person or entity filing.
        shares_before: Shares held before the event.
        shares_after: Shares held after the event.
        change_pct: Percentage change in holdings.
        event_date: Date of the governance event.
        source_url: URL of the source disclosure.
        ingested_at: Timestamp when the data was ingested.
    """

    __tablename__ = "governance_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("instruments.symbol"),
        nullable=False,
        index=True,
    )
    flag_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    filer_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    shares_before: Mapped[int | None] = mapped_column(Numeric(18, 0), nullable=True)
    shares_after: Mapped[int | None] = mapped_column(Numeric(18, 0), nullable=True)
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    instrument = relationship("IdxEquityInstrument", back_populates="governance_flags", lazy="selectin")

    __table_args__ = (
        Index(
            "ix_idx_equity_governance_flags_symbol_date",
            "symbol",
            event_date.desc(),
        ),
        Index("ix_idx_equity_governance_flags_type", "flag_type"),
        Index("ix_idx_equity_governance_flags_severity", "severity"),
    )
