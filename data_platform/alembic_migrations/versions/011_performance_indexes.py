"""Add performance indexes for production query patterns.

Creates partial indexes, expression indexes, and a BRIN index that
cannot be auto-generated from ORM model definitions.

Revision ID: 011
Create Date: 2026-03-10 00:02:00.000000
"""

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create performance indexes."""
    # Partial index: only active instruments for symbol lookups
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_instruments_active_symbol "
        "ON market_data.idx_equity_instrument (symbol) "
        "WHERE is_active = TRUE"
    )

    # Partial index: open orders only (common query pattern)
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_orders_open "
        "ON trading.strategy_order_lifecycle_record "
        "(strategy_id, symbol, created_at DESC) "
        "WHERE status IN ('pending_risk', 'risk_approved', 'submitted', "
        "'acknowledged', 'partial_fill')"
    )

    # BRIN index: efficient for append-only time-series data
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ohlcv_brin_time "
        "ON market_data.idx_equity_ohlcv_tick "
        "USING BRIN (time) WITH (pages_per_range = 128)"
    )


def downgrade() -> None:
    """Drop all performance indexes."""
    op.execute("DROP INDEX IF EXISTS market_data.ix_ohlcv_brin_time")
    op.execute("DROP INDEX IF EXISTS trading.ix_orders_open")
    op.execute("DROP INDEX IF EXISTS market_data.ix_instruments_active_symbol")
