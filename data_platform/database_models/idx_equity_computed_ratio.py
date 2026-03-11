"""IDX equity pre-computed valuation and quality ratios.

Stores daily snapshots of key financial ratios derived from price and
fundamental data, enabling fast screening and ranking queries.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal


class IdxEquityComputedRatio(Base):
    """Pre-computed financial ratios for an IDX equity on a given date.

    Attributes:
        id: Primary key (UUID).
        symbol: Ticker symbol (FK to instruments).
        date: Computation date.
        pe_ratio: Price-to-earnings ratio.
        pb_ratio: Price-to-book ratio.
        roe_pct: Return on equity as a percentage.
        roa_pct: Return on assets as a percentage.
        dividend_yield_pct: Dividend yield as a percentage.
        eps: Earnings per share.
        debt_to_equity: Debt-to-equity ratio.
        current_ratio: Current ratio.
        market_cap_idr: Market capitalisation in IDR.
        computed_at: Timestamp when the ratios were computed.
    """

    __tablename__ = "computed_ratios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("instruments.symbol"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    pb_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    roe_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    roa_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    dividend_yield_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    eps: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    current_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    market_cap_idr: Mapped[int | None] = mapped_column(BigInteger)
    computed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "ix_idx_equity_computed_ratios_symbol_date",
            "symbol",
            date.desc(),
        ),
        Index("ix_idx_equity_computed_ratios_pe", "pe_ratio"),
        Index("ix_idx_equity_computed_ratios_roe", "roe_pct"),
    )
