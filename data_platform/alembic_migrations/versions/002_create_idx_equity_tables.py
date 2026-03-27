"""Create IDX equity tables: instruments, OHLCV ticks, financials, ratios, actions, news.

Revision ID: 002
Create Date: 2024-01-01 00:01:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all IDX equity tables with TimescaleDB hypertable for OHLCV."""
    # Instrument master
    op.create_table(
        "idx_equity_instrument",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("symbol", sa.String(20), unique=True, nullable=False, index=True),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("sector", sa.String(100)),
        sa.Column("sub_sector", sa.String(100)),
        sa.Column("board", sa.String(30)),
        sa.Column("listing_date", sa.Date()),
        sa.Column("shares_outstanding", sa.BigInteger()),
        sa.Column("market_cap_idr", sa.Numeric(20, 0)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="market_data",
    )

    # OHLCV ticks (TimescaleDB hypertable)
    op.create_table(
        "idx_equity_ohlcv_tick",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("exchange", sa.String(20), server_default="IDX"),
        sa.Column("interval", sa.String(10), nullable=False),
        sa.Column("open", sa.Numeric(18, 6)),
        sa.Column("high", sa.Numeric(18, 6)),
        sa.Column("low", sa.Numeric(18, 6)),
        sa.Column("close", sa.Numeric(18, 6)),
        sa.Column("adjusted_close", sa.Numeric(18, 6)),
        sa.Column("volume", sa.BigInteger()),
        sa.Column("vwap", sa.Numeric(18, 6)),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="market_data",
    )
    op.create_primary_key("pk_ohlcv_tick", "idx_equity_ohlcv_tick", ["time", "symbol"], schema="market_data")
    try:
        conn = op.get_bind()
        nested = conn.begin_nested()
        conn.execute(text("SELECT create_hypertable('market_data.idx_equity_ohlcv_tick', 'time')"))
        nested.commit()
    except Exception:
        nested.rollback()

    # Financial statements
    op.create_table(
        "idx_equity_financial_statement",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("statement_type", sa.String(30), nullable=False),
        sa.Column("revenue_idr", sa.Numeric(20, 0)),
        sa.Column("gross_profit_idr", sa.Numeric(20, 0)),
        sa.Column("operating_income_idr", sa.Numeric(20, 0)),
        sa.Column("net_income_idr", sa.Numeric(20, 0)),
        sa.Column("total_assets_idr", sa.Numeric(20, 0)),
        sa.Column("total_liabilities_idr", sa.Numeric(20, 0)),
        sa.Column("total_equity_idr", sa.Numeric(20, 0)),
        sa.Column("operating_cash_flow_idr", sa.Numeric(20, 0)),
        sa.Column("capital_expenditure_idr", sa.Numeric(20, 0)),
        sa.Column("free_cash_flow_idr", sa.Numeric(20, 0)),
        sa.Column("filing_date", sa.Date()),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="market_data",
    )
    op.create_index(
        "ix_financial_stmt_symbol_period", "idx_equity_financial_statement", ["symbol", "period"], schema="market_data"
    )

    # Computed ratios
    op.create_table(
        "idx_equity_computed_ratio",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("pe_ratio", sa.Numeric(12, 4)),
        sa.Column("pb_ratio", sa.Numeric(12, 4)),
        sa.Column("roe_pct", sa.Numeric(8, 4)),
        sa.Column("roa_pct", sa.Numeric(8, 4)),
        sa.Column("dividend_yield_pct", sa.Numeric(8, 4)),
        sa.Column("eps", sa.Numeric(18, 6)),
        sa.Column("debt_to_equity", sa.Numeric(12, 4)),
        sa.Column("current_ratio", sa.Numeric(12, 4)),
        sa.Column("market_cap_idr", sa.Numeric(20, 0)),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="market_data",
    )
    op.create_index(
        "ix_computed_ratio_symbol_date",
        "idx_equity_computed_ratio",
        ["symbol", "date"],
        schema="market_data",
        unique=True,
    )

    # Corporate actions
    op.create_table(
        "idx_equity_corporate_action",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("ex_date", sa.Date()),
        sa.Column("record_date", sa.Date()),
        sa.Column("payment_date", sa.Date()),
        sa.Column("value", sa.Numeric(18, 6)),
        sa.Column("description", sa.Text()),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="market_data",
    )

    # Index constituents
    op.create_table(
        "idx_equity_index_constituent",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("index_name", sa.String(20), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("removal_date", sa.Date()),
        sa.Column("weight_pct", sa.Numeric(8, 4)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="market_data",
    )
    op.create_index(
        "ix_index_constituent_index_symbol",
        "idx_equity_index_constituent",
        ["index_name", "symbol"],
        schema="market_data",
    )

    # News articles
    op.create_table(
        "idx_equity_news_article",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("url", sa.String(2000), unique=True, nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("content_text", sa.Text()),
        sa.Column("symbols", sa.ARRAY(sa.String(20))),
        sa.Column("sentiment_score", sa.Numeric(6, 4)),
        sa.Column("sentiment_label", sa.String(20)),
        sa.Column("language", sa.String(10), server_default="id"),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="market_data",
    )


def downgrade() -> None:
    """Drop all IDX equity tables."""
    op.drop_table("idx_equity_news_article", schema="market_data")
    op.drop_table("idx_equity_index_constituent", schema="market_data")
    op.drop_table("idx_equity_corporate_action", schema="market_data")
    op.drop_table("idx_equity_computed_ratio", schema="market_data")
    op.drop_table("idx_equity_financial_statement", schema="market_data")
    op.drop_table("idx_equity_ohlcv_tick", schema="market_data")
    op.drop_table("idx_equity_instrument", schema="market_data")
