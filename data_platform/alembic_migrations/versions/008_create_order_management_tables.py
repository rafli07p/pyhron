"""Create order management tables: orders, positions, trade executions.

Revision ID: 008
Create Date: 2024-01-01 00:07:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create order lifecycle, position snapshot, and trade execution tables."""
    # Order lifecycle record
    op.create_table(
        "strategy_order_lifecycle_record",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("client_order_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("broker_order_id", sa.String(128)),
        sa.Column("strategy_id", sa.String(100), nullable=False, index=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("time_in_force", sa.String(10), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("limit_price", sa.Numeric(18, 6)),
        sa.Column("stop_price", sa.Numeric(18, 6)),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("filled_quantity", sa.BigInteger(), server_default="0"),
        sa.Column("avg_fill_price", sa.Numeric(18, 6)),
        sa.Column("commission", sa.Numeric(18, 6), server_default="0"),
        sa.Column("tax", sa.Numeric(18, 6), server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("acknowledged_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("filled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="trading",
    )

    # Position snapshot (current holdings per strategy)
    op.create_table(
        "strategy_position_current_snapshot",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("strategy_id", sa.String(100), nullable=False, index=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("avg_entry_price", sa.Numeric(18, 6)),
        sa.Column("current_price", sa.Numeric(18, 6)),
        sa.Column("market_value", sa.Numeric(20, 4)),
        sa.Column("unrealized_pnl", sa.Numeric(20, 4)),
        sa.Column("realized_pnl", sa.Numeric(20, 4), server_default="0"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="trading",
    )
    op.create_index(
        "ix_position_strategy_symbol",
        "strategy_position_current_snapshot",
        ["strategy_id", "symbol"],
        schema="trading",
        unique=True,
    )

    # Trade execution log (immutable fill records)
    op.create_table(
        "strategy_trade_execution_log",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("client_order_id", sa.String(64), nullable=False, index=True),
        sa.Column("broker_order_id", sa.String(128)),
        sa.Column("strategy_id", sa.String(100), nullable=False, index=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("filled_quantity", sa.BigInteger(), nullable=False),
        sa.Column("filled_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("commission", sa.Numeric(18, 6), server_default="0"),
        sa.Column("tax", sa.Numeric(18, 6), server_default="0"),
        sa.Column("execution_venue", sa.String(50)),
        sa.Column("executed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="trading",
    )


def downgrade() -> None:
    """Drop order management tables."""
    op.drop_table("strategy_trade_execution_log", schema="trading")
    op.drop_table("strategy_position_current_snapshot", schema="trading")
    op.drop_table("strategy_order_lifecycle_record", schema="trading")
