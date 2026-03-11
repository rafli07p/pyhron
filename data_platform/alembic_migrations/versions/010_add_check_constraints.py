"""Add CHECK constraints to existing tables.

Adds data-integrity constraints to OHLCV, order lifecycle, and position
snapshot tables that were missing from the original migrations.

Revision ID: 010
Create Date: 2026-03-10 00:01:00.000000
"""

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add CHECK constraints to existing tables."""
    # OHLCV: high must be >= low
    op.execute("ALTER TABLE market_data.idx_equity_ohlcv_tick ADD CONSTRAINT ck_ohlcv_high_gte_low CHECK (high >= low)")

    # OHLCV: volume must be non-negative
    op.execute(
        "ALTER TABLE market_data.idx_equity_ohlcv_tick "
        "ADD CONSTRAINT ck_ohlcv_volume_non_negative CHECK (volume IS NULL OR volume >= 0)"
    )

    # Orders: filled_quantity must not exceed total quantity
    op.execute(
        "ALTER TABLE trading.strategy_order_lifecycle_record "
        "ADD CONSTRAINT ck_orders_filled_lte_quantity CHECK (filled_quantity <= quantity)"
    )

    # Positions: quantity must be non-negative (no naked shorts on IDX)
    op.execute(
        "ALTER TABLE trading.strategy_position_current_snapshot "
        "ADD CONSTRAINT ck_positions_quantity_non_negative CHECK (quantity >= 0)"
    )


def downgrade() -> None:
    """Drop all added CHECK constraints."""
    op.execute(
        "ALTER TABLE trading.strategy_position_current_snapshot "
        "DROP CONSTRAINT IF EXISTS ck_positions_quantity_non_negative"
    )
    op.execute(
        "ALTER TABLE trading.strategy_order_lifecycle_record DROP CONSTRAINT IF EXISTS ck_orders_filled_lte_quantity"
    )
    op.execute("ALTER TABLE market_data.idx_equity_ohlcv_tick DROP CONSTRAINT IF EXISTS ck_ohlcv_volume_non_negative")
    op.execute("ALTER TABLE market_data.idx_equity_ohlcv_tick DROP CONSTRAINT IF EXISTS ck_ohlcv_high_gte_low")
