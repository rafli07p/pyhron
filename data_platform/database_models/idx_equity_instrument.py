"""IDX equity instrument master registry.

Provides the canonical reference for all listed equities on the Indonesia
Stock Exchange, including sector classification and listing lifecycle dates.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, Index, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class IdxEquityInstrument(Base):
    """Master instrument registry for IDX-listed equities.

    Attributes:
        symbol: Ticker symbol (e.g. ``"BBCA"``).
        isin: ISIN code, unique when present.
        name: Full company name.
        exchange: Exchange mic code (e.g. ``"XIDX"``).
        sector: IDX sector classification.
        industry: IDX industry sub-classification.
        market_cap: Last-known market capitalisation in IDR.
        shares_outstanding: Total shares outstanding.
        lot_size: Standard lot size (default 100).
        currency: Trading currency ISO code.
        is_active: Whether the instrument is currently listed.
        listing_date: Date the instrument was first listed.
        delisting_date: Date the instrument was delisted, if applicable.
        created_at: Row creation timestamp.
        updated_at: Row last-update timestamp.
    """

    __tablename__ = "idx_equity_instruments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(10))
    sector: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(100))
    market_cap: Mapped[int | None] = mapped_column(BigInteger)
    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger)
    lot_size: Mapped[int] = mapped_column(Integer, default=100)
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delisting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_idx_equity_instruments_exchange_active", "exchange", "is_active"),
        Index("ix_idx_equity_instruments_sector_active", "sector", "is_active"),
    )
