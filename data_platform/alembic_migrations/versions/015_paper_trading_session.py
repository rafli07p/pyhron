"""Create paper trading session, NAV snapshot, and P&L attribution tables.

Revision ID: 015
Revises: 014
Create Date: 2026-03-13 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Paper trading session
    op.create_table(
        "paper_trading_sessions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "strategy_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="INITIALIZING",
        ),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("initial_capital_idr", sa.Numeric(20, 2), nullable=False),
        sa.Column("current_nav_idr", sa.Numeric(20, 2), nullable=False),
        sa.Column("peak_nav_idr", sa.Numeric(20, 2), nullable=False),
        sa.Column(
            "max_drawdown_pct",
            sa.Numeric(8, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_trades",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "winning_trades",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "realized_pnl_idr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_commission_idr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "cash_idr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "unsettled_cash_idr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.CheckConstraint("initial_capital_idr > 0", name="ck_paper_session_capital_positive"),
        sa.CheckConstraint(
            "status IN ('INITIALIZING', 'RUNNING', 'PAUSED', 'STOPPED', 'COMPLETED')",
            name="ck_paper_session_status_valid",
        ),
        sa.CheckConstraint(
            "mode IN ('LIVE_HOURS', 'SIMULATION')",
            name="ck_paper_session_mode_valid",
        ),
    )

    op.create_index(
        "ix_paper_trading_session_status",
        "paper_trading_sessions",
        ["status"],
        postgresql_where=sa.text("status IN ('RUNNING', 'PAUSED')"),
    )

    op.create_index(
        "ix_paper_trading_session_strategy",
        "paper_trading_sessions",
        ["strategy_id", sa.text("created_at DESC")],
    )

    # Paper NAV snapshot
    op.create_table(
        "paper_nav_snapshots",
        sa.Column(
            "session_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("paper_trading_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nav_idr", sa.Numeric(20, 2), nullable=False),
        sa.Column("cash_idr", sa.Numeric(20, 2), nullable=False),
        sa.Column("gross_exposure_idr", sa.Numeric(20, 2), nullable=False),
        sa.Column("drawdown_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("daily_pnl_idr", sa.Numeric(20, 2), nullable=False),
        sa.Column("daily_return_pct", sa.Numeric(10, 6), nullable=False),
        sa.PrimaryKeyConstraint("session_id", "timestamp"),
    )

    op.execute(
        "SELECT create_hypertable('paper_nav_snapshots', 'timestamp', " "chunk_time_interval => INTERVAL '1 day')"
    )

    op.create_index(
        "ix_paper_nav_snapshot_session",
        "paper_nav_snapshots",
        ["session_id", sa.text("timestamp DESC")],
    )

    # Paper P&L attribution
    op.create_table(
        "paper_pnl_attributions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "session_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("paper_trading_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "realized_pnl_idr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "unrealized_pnl_idr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "commission_idr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "turnover_idr",
            sa.Numeric(20, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "trades_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("signal_source", sa.String(50), nullable=True),
        sa.Column("alpha_score", sa.Numeric(10, 6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("session_id", "symbol", "date", name="uq_paper_pnl_session_symbol_date"),
    )

    op.create_index(
        "ix_paper_pnl_attribution_session_date",
        "paper_pnl_attributions",
        ["session_id", sa.text("date DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_paper_pnl_attribution_session_date", table_name="paper_pnl_attributions")
    op.drop_table("paper_pnl_attributions")
    op.drop_index("ix_paper_nav_snapshot_session", table_name="paper_nav_snapshots")
    op.drop_table("paper_nav_snapshots")
    op.drop_index("ix_paper_trading_session_status", table_name="paper_trading_sessions")
    op.drop_index("ix_paper_trading_session_strategy", table_name="paper_trading_sessions")
    op.drop_table("paper_trading_sessions")
