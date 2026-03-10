"""IDX equity financial statement model.

Stores quarterly and annual fundamentals sourced from IDX filings or
third-party providers such as EODHD.
"""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.async_database_session import Base

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal


class StatementType(enum.StrEnum):
    """Financial statement type."""

    INCOME = "income"
    BALANCE = "balance"
    CASHFLOW = "cashflow"


class IdxEquityFinancialStatement(Base):
    """Quarterly or annual financial statement for an IDX equity.

    Attributes:
        id: Primary key (UUID).
        symbol: Ticker symbol (FK to instruments).
        period_end: Period end date.
        fiscal_year: Fiscal year.
        quarter: Fiscal quarter (1-4), null for annual statements.
        statement_type: One of income, balance, or cashflow.
        revenue: Total revenue in IDR.
        gross_profit: Gross profit in IDR.
        ebit: Earnings before interest and taxes.
        ebitda: EBITDA.
        net_income: Net income in IDR.
        total_assets: Total assets.
        total_liabilities: Total liabilities.
        total_equity: Total equity.
        total_debt: Total debt.
        cash_and_equivalents: Cash and cash equivalents.
        operating_cash_flow: Operating cash flow.
        capex: Capital expenditures.
        free_cash_flow: Free cash flow.
        shares_outstanding: Shares outstanding at period end.
        eps: Earnings per share.
        source_url: URL of the original filing.
        created_at: Row creation timestamp.
    """

    __tablename__ = "idx_equity_financial_statements"

    # ── Relationships ────────────────────────────────────────────────────────
    instrument = relationship(
        "IdxEquityInstrument", back_populates="financial_statements", lazy="selectin"
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("idx_equity_instruments.symbol"),
        nullable=False,
        index=True,
    )
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    statement_type: Mapped[StatementType] = mapped_column(
        Enum(StatementType, name="statement_type_enum"), nullable=False
    )

    # Income statement
    revenue: Mapped[int | None] = mapped_column(BigInteger)
    gross_profit: Mapped[int | None] = mapped_column(BigInteger)
    ebit: Mapped[int | None] = mapped_column(BigInteger)
    ebitda: Mapped[int | None] = mapped_column(BigInteger)
    net_income: Mapped[int | None] = mapped_column(BigInteger)

    # Balance sheet
    total_assets: Mapped[int | None] = mapped_column(BigInteger)
    total_liabilities: Mapped[int | None] = mapped_column(BigInteger)
    total_equity: Mapped[int | None] = mapped_column(BigInteger)
    total_debt: Mapped[int | None] = mapped_column(BigInteger)
    cash_and_equivalents: Mapped[int | None] = mapped_column(BigInteger)

    # Cash flow
    operating_cash_flow: Mapped[int | None] = mapped_column(BigInteger)
    capex: Mapped[int | None] = mapped_column(BigInteger)
    free_cash_flow: Mapped[int | None] = mapped_column(BigInteger)

    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger)
    eps: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    source_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("symbol", "period_end", "statement_type"),
        CheckConstraint(
            "quarter IS NULL OR (quarter >= 1 AND quarter <= 4)",
            name="quarter_range",
        ),
        Index(
            "ix_idx_equity_financial_statements_symbol_period",
            "symbol",
            period_end.desc(),
        ),
    )
