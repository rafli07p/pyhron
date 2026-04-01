"""IDX equity instrument master registry.

Provides the canonical reference for all listed equities on the Indonesia
Stock Exchange, including sector classification and listing lifecycle dates.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import BigInteger, Boolean, Date, Index, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.async_database_session import Base


class IdxEquityInstrument(Base):
    """Master instrument registry for IDX-listed equities.

    Column names match the canonical schema after migration 013.
    """

    __tablename__ = "instruments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100))
    sub_sector: Mapped[str | None] = mapped_column(String(100))
    board: Mapped[str | None] = mapped_column(String(30))
    listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger)
    market_cap_idr: Mapped[int | None] = mapped_column("market_cap_idr", BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default="now()",
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships - use noload to avoid eager loading column-mismatched tables
    financial_statements = relationship(
        "IdxEquityFinancialStatement", back_populates="instrument", lazy="noload"
    )
    corporate_actions = relationship(
        "IdxEquityCorporateAction", back_populates="instrument", lazy="noload"
    )
    computed_ratios = relationship(
        "IdxEquityComputedRatio", back_populates="instrument", lazy="noload"
    )
    governance_flags = relationship(
        "IdxEquityGovernanceFlag", back_populates="instrument", lazy="noload"
    )
    index_memberships = relationship(
        "IdxEquityIndexConstituent", back_populates="instrument", lazy="noload"
    )

    __table_args__ = (
        Index(
            "ix_instruments_active_symbol",
            "symbol",
            postgresql_where="is_active = true",
        ),
    )
