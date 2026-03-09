"""Market data ORM models.

Tables:
  - market_ticks: TimescaleDB hypertable for OHLCV tick data
  - instruments: Master instrument registry
  - index_constituents: Index membership history
  - financial_statements: Quarterly/annual fundamentals
  - computed_ratios: Pre-computed valuation and quality metrics
  - corporate_actions: Dividends, splits, rights issues
  - news_articles: Aggregated news with sentiment
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


# ── Enums ───────────────────────────────────────────────────────────────────


class StatementType(str, enum.Enum):
    INCOME = "income"
    BALANCE = "balance"
    CASHFLOW = "cashflow"


class ActionType(str, enum.Enum):
    CASH_DIVIDEND = "cash_dividend"
    STOCK_DIVIDEND = "stock_dividend"
    SPLIT = "split"
    REVERSE_SPLIT = "reverse_split"
    RIGHTS = "rights"


class SentimentLabel(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ── MarketTick ──────────────────────────────────────────────────────────────


class MarketTick(Base):
    """TimescaleDB hypertable for OHLCV tick data.

    Partitioned by time (7-day chunks). Composite PK on (time, symbol, exchange).
    """

    __tablename__ = "market_ticks"

    time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), primary_key=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), primary_key=True, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=True)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=True)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=True)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    bid: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    ask: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)

    __table_args__ = (
        Index("ix_market_ticks_symbol_time", "symbol", time.desc()),
        Index("ix_market_ticks_exchange_symbol_time", "exchange", "symbol", time.desc()),
    )


# ── Instrument ──────────────────────────────────────────────────────────────


class Instrument(Base):
    """Master instrument registry."""

    __tablename__ = "instruments"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    isin: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
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
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_instruments_exchange_active", "exchange", "is_active"),
        Index("ix_instruments_sector_active", "sector", "is_active"),
    )


# ── IndexConstituent ────────────────────────────────────────────────────────


class IndexConstituent(Base):
    """Index membership history (e.g. LQ45, IDX80)."""

    __tablename__ = "index_constituents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    index_name: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    removal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("index_name", "symbol", "effective_date"),
        CheckConstraint("weight BETWEEN 0 AND 1", name="weight_range"),
    )


# ── FinancialStatement ──────────────────────────────────────────────────────


class FinancialStatement(Base):
    """Quarterly/annual fundamentals from EODHD or IDX filings."""

    __tablename__ = "financial_statements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
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
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint("symbol", "period_end", "statement_type"),
        CheckConstraint("quarter IS NULL OR (quarter >= 1 AND quarter <= 4)", name="quarter_range"),
    )


# ── ComputedRatio ───────────────────────────────────────────────────────────


class ComputedRatio(Base):
    """Pre-computed valuation and quality metrics."""

    __tablename__ = "computed_ratios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    price_used: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    # Valuation
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    pb_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    ps_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    ev_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    # Quality
    roe: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    roa: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    roce: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    current_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    quick_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    # Margins
    gross_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    operating_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    net_margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))

    # Growth
    revenue_growth_yoy: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    earnings_growth_yoy: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))

    # Income
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    payout_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))

    __table_args__ = (
        Index("ix_computed_ratios_symbol_at", "symbol", computed_at.desc()),
        Index("ix_computed_ratios_pe", "pe_ratio"),
        Index("ix_computed_ratios_roe", "roe"),
    )


# ── CorporateAction ────────────────────────────────────────────────────────


class CorporateAction(Base):
    """Dividends, splits, rights issues."""

    __tablename__ = "corporate_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType, name="action_type_enum"), nullable=False
    )
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    record_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint("symbol", "action_type", "ex_date"),
    )


# ── NewsArticle ─────────────────────────────────────────────────────────────


class NewsArticle(Base):
    """Aggregated news with NLP annotations."""

    __tablename__ = "news_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source: Mapped[str | None] = mapped_column(String(100))
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    content_summary: Mapped[str | None] = mapped_column(Text)
    full_content: Mapped[str | None] = mapped_column(Text)
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    sentiment_label: Mapped[SentimentLabel | None] = mapped_column(
        Enum(SentimentLabel, name="sentiment_label_enum")
    )
    mentioned_tickers: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    __table_args__ = (
        Index("ix_news_published_at", published_at.desc()),
        Index("ix_news_tickers", "mentioned_tickers", postgresql_using="gin"),
        CheckConstraint(
            "sentiment_score IS NULL OR (sentiment_score BETWEEN -1 AND 1)",
            name="sentiment_range",
        ),
    )
