"""Initial schema with TimescaleDB hypertables.

Revision ID: 001
Create Date: 2026-03-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Extensions -----------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # -- Enum types -----------------------------------------------------------
    statement_type = postgresql.ENUM(
        "income", "balance", "cashflow", name="statement_type_enum", create_type=False
    )
    action_type = postgresql.ENUM(
        "cash_dividend", "stock_dividend", "split", "reverse_split", "rights",
        name="action_type_enum", create_type=False,
    )
    sentiment_label = postgresql.ENUM(
        "positive", "negative", "neutral", name="sentiment_label_enum", create_type=False
    )
    order_side = postgresql.ENUM("buy", "sell", name="order_side_enum", create_type=False)
    order_type = postgresql.ENUM(
        "market", "limit", "stop", "stop_limit", name="order_type_enum", create_type=False
    )
    time_in_force = postgresql.ENUM(
        "day", "gtc", "ioc", "fok", name="time_in_force_enum", create_type=False
    )
    order_status = postgresql.ENUM(
        "pending_risk", "risk_approved", "risk_rejected", "submitted",
        "acknowledged", "partial_fill", "filled", "cancelled", "rejected", "expired",
        name="order_status_enum", create_type=False,
    )

    for enum in [statement_type, action_type, sentiment_label, order_side,
                 order_type, time_in_force, order_status]:
        enum.create(op.get_bind(), checkfirst=True)

    # -- market_ticks ---------------------------------------------------------
    op.create_table(
        "market_ticks",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("open", sa.Numeric(18, 6)),
        sa.Column("high", sa.Numeric(18, 6)),
        sa.Column("low", sa.Numeric(18, 6)),
        sa.Column("close", sa.Numeric(18, 6)),
        sa.Column("volume", sa.BigInteger),
        sa.Column("vwap", sa.Numeric(18, 6)),
        sa.Column("bid", sa.Numeric(18, 6)),
        sa.Column("ask", sa.Numeric(18, 6)),
        sa.Column("adjusted_close", sa.Numeric(18, 6)),
        sa.PrimaryKeyConstraint("time", "symbol", "exchange"),
    )
    op.execute(
        "SELECT create_hypertable('market_ticks', 'time', "
        "chunk_time_interval => INTERVAL '7 days')"
    )
    op.create_index("ix_market_ticks_symbol_time", "market_ticks", ["symbol", sa.text("time DESC")])
    op.create_index(
        "ix_market_ticks_exchange_symbol_time", "market_ticks",
        ["exchange", "symbol", sa.text("time DESC")],
    )

    # -- instruments ----------------------------------------------------------
    op.create_table(
        "instruments",
        sa.Column("symbol", sa.String(20), primary_key=True),
        sa.Column("isin", sa.String(12), unique=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("exchange", sa.String(10)),
        sa.Column("sector", sa.String(100)),
        sa.Column("industry", sa.String(100)),
        sa.Column("market_cap", sa.BigInteger),
        sa.Column("shares_outstanding", sa.BigInteger),
        sa.Column("lot_size", sa.Integer, server_default="100"),
        sa.Column("currency", sa.String(3), server_default="'IDR'"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("listing_date", sa.Date),
        sa.Column("delisting_date", sa.Date),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_instruments_exchange_active", "instruments", ["exchange", "is_active"])
    op.create_index("ix_instruments_sector_active", "instruments", ["sector", "is_active"])

    # -- index_constituents ---------------------------------------------------
    op.create_table(
        "index_constituents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("index_name", sa.String(20), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("weight", sa.Numeric(8, 6), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("removal_date", sa.Date),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.UniqueConstraint("index_name", "symbol", "effective_date"),
        sa.CheckConstraint("weight BETWEEN 0 AND 1", name="weight_range"),
    )

    # -- financial_statements -------------------------------------------------
    op.create_table(
        "financial_statements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("fiscal_year", sa.Integer, nullable=False),
        sa.Column("quarter", sa.Integer),
        sa.Column("statement_type", statement_type, nullable=False),
        sa.Column("revenue", sa.BigInteger),
        sa.Column("gross_profit", sa.BigInteger),
        sa.Column("ebit", sa.BigInteger),
        sa.Column("ebitda", sa.BigInteger),
        sa.Column("net_income", sa.BigInteger),
        sa.Column("total_assets", sa.BigInteger),
        sa.Column("total_liabilities", sa.BigInteger),
        sa.Column("total_equity", sa.BigInteger),
        sa.Column("total_debt", sa.BigInteger),
        sa.Column("cash_and_equivalents", sa.BigInteger),
        sa.Column("operating_cash_flow", sa.BigInteger),
        sa.Column("capex", sa.BigInteger),
        sa.Column("free_cash_flow", sa.BigInteger),
        sa.Column("shares_outstanding", sa.BigInteger),
        sa.Column("eps", sa.Numeric(18, 6)),
        sa.Column("source_url", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("symbol", "period_end", "statement_type"),
        sa.CheckConstraint("quarter IS NULL OR (quarter >= 1 AND quarter <= 4)", name="quarter_range"),
    )

    # -- computed_ratios ------------------------------------------------------
    op.create_table(
        "computed_ratios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("price_used", sa.Numeric(18, 6), nullable=False),
        sa.Column("pe_ratio", sa.Numeric(10, 4)),
        sa.Column("pb_ratio", sa.Numeric(10, 4)),
        sa.Column("ps_ratio", sa.Numeric(10, 4)),
        sa.Column("ev_ebitda", sa.Numeric(10, 4)),
        sa.Column("roe", sa.Numeric(8, 6)),
        sa.Column("roa", sa.Numeric(8, 6)),
        sa.Column("roce", sa.Numeric(8, 6)),
        sa.Column("debt_to_equity", sa.Numeric(10, 4)),
        sa.Column("current_ratio", sa.Numeric(8, 4)),
        sa.Column("quick_ratio", sa.Numeric(8, 4)),
        sa.Column("gross_margin", sa.Numeric(8, 6)),
        sa.Column("operating_margin", sa.Numeric(8, 6)),
        sa.Column("net_margin", sa.Numeric(8, 6)),
        sa.Column("revenue_growth_yoy", sa.Numeric(8, 6)),
        sa.Column("earnings_growth_yoy", sa.Numeric(8, 6)),
        sa.Column("dividend_yield", sa.Numeric(8, 6)),
        sa.Column("payout_ratio", sa.Numeric(8, 6)),
    )
    op.create_index("ix_computed_ratios_symbol_at", "computed_ratios", ["symbol", sa.text("computed_at DESC")])
    op.create_index("ix_computed_ratios_pe", "computed_ratios", ["pe_ratio"])
    op.create_index("ix_computed_ratios_roe", "computed_ratios", ["roe"])

    # -- corporate_actions ----------------------------------------------------
    op.create_table(
        "corporate_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("action_type", action_type, nullable=False),
        sa.Column("ex_date", sa.Date, nullable=False),
        sa.Column("record_date", sa.Date),
        sa.Column("payment_date", sa.Date),
        sa.Column("amount", sa.Numeric(18, 6)),
        sa.Column("ratio", sa.Numeric(10, 6)),
        sa.Column("currency", sa.String(3), server_default="'IDR'"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("symbol", "action_type", "ex_date"),
    )

    # -- news_articles --------------------------------------------------------
    op.create_table(
        "news_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("url", sa.Text, unique=True, nullable=False),
        sa.Column("source", sa.String(100)),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("content_summary", sa.Text),
        sa.Column("full_content", sa.Text),
        sa.Column("sentiment_score", sa.Numeric(4, 3)),
        sa.Column("sentiment_label", sentiment_label),
        sa.Column("mentioned_tickers", postgresql.ARRAY(sa.String), server_default="'{}'"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "sentiment_score IS NULL OR (sentiment_score BETWEEN -1 AND 1)",
            name="sentiment_range",
        ),
    )
    op.create_index("ix_news_published_at", "news_articles", [sa.text("published_at DESC")])
    op.execute(
        "CREATE INDEX ix_news_tickers ON news_articles USING gin (mentioned_tickers)"
    )

    # -- orders ---------------------------------------------------------------
    op.create_table(
        "orders",
        sa.Column("client_order_id", sa.String(36), primary_key=True),
        sa.Column("broker_order_id", sa.String(100)),
        sa.Column("strategy_id", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(10)),
        sa.Column("side", order_side, nullable=False),
        sa.Column("order_type", order_type, nullable=False),
        sa.Column("quantity", sa.BigInteger, nullable=False),
        sa.Column("filled_quantity", sa.BigInteger, server_default="0"),
        sa.Column("limit_price", sa.Numeric(18, 6)),
        sa.Column("stop_price", sa.Numeric(18, 6)),
        sa.Column("avg_fill_price", sa.Numeric(18, 6)),
        sa.Column("status", order_status, nullable=False, server_default="'pending_risk'"),
        sa.Column("currency", sa.String(3)),
        sa.Column("time_in_force", time_in_force),
        sa.Column("commission", sa.Numeric(18, 6), server_default="0"),
        sa.Column("tax", sa.Numeric(18, 6), server_default="0"),
        sa.Column("signal_time", sa.TIMESTAMP(timezone=True)),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("acknowledged_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("filled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_orders_strategy_created", "orders", ["strategy_id", sa.text("created_at DESC")])
    op.create_index("ix_orders_symbol_status", "orders", ["symbol", "status"])
    op.create_index("ix_orders_broker_id", "orders", ["broker_order_id"])

    # -- positions ------------------------------------------------------------
    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("strategy_id", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(10)),
        sa.Column("quantity", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("avg_entry_price", sa.Numeric(18, 6)),
        sa.Column("current_price", sa.Numeric(18, 6)),
        sa.Column("unrealized_pnl", sa.Numeric(18, 6)),
        sa.Column("realized_pnl", sa.Numeric(18, 6)),
        sa.Column("market_value", sa.Numeric(18, 6)),
        sa.Column("last_updated", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("strategy_id", "symbol", "exchange"),
    )

    # -- trades ---------------------------------------------------------------
    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("client_order_id", sa.String(36), nullable=False),
        sa.Column("broker_trade_id", sa.String(100)),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(10)),
        sa.Column("side", order_side, nullable=False),
        sa.Column("quantity", sa.BigInteger, nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("commission", sa.Numeric(18, 6), server_default="0"),
        sa.Column("tax", sa.Numeric(18, 6), server_default="0"),
        sa.Column("trade_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.execute(
        "SELECT create_hypertable('trades', 'trade_time', "
        "chunk_time_interval => INTERVAL '30 days')"
    )
    op.create_index("ix_trades_order_id", "trades", ["client_order_id"])
    op.create_index("ix_trades_symbol_time", "trades", ["symbol", sa.text("trade_time DESC")])

    # -- risk_limits ----------------------------------------------------------
    op.create_table(
        "risk_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("strategy_id", sa.String(100), unique=True, nullable=False),
        sa.Column("max_position_size_pct", sa.Numeric(5, 4), server_default="0.10"),
        sa.Column("max_sector_concentration_pct", sa.Numeric(5, 4), server_default="0.30"),
        sa.Column("daily_loss_limit_pct", sa.Numeric(5, 4), server_default="0.02"),
        sa.Column("max_gross_exposure_pct", sa.Numeric(5, 4), server_default="1.00"),
        sa.Column("max_var_95_pct", sa.Numeric(5, 4), server_default="0.05"),
        sa.Column("max_orders_per_minute", sa.Integer, server_default="60"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    # Drop hypertables first (they have special dependencies)
    op.execute("DROP TABLE IF EXISTS trades CASCADE")
    op.execute("DROP TABLE IF EXISTS market_ticks CASCADE")

    op.drop_table("risk_limits")
    op.drop_table("positions")
    op.drop_table("orders")
    op.drop_table("news_articles")
    op.drop_table("corporate_actions")
    op.drop_table("computed_ratios")
    op.drop_table("financial_statements")
    op.drop_table("index_constituents")
    op.drop_table("instruments")

    for name in [
        "order_status_enum", "time_in_force_enum", "order_type_enum",
        "order_side_enum", "sentiment_label_enum", "action_type_enum",
        "statement_type_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
