"""Create user, strategy, backtest_run, and signal tables.

Revision ID: 009
Create Date: 2026-03-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create enum types and tables for users, strategies, backtests, and signals."""
    # ── Enum types ────────────────────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN CREATE TYPE user_role AS ENUM ('admin', 'trader', 'analyst', 'readonly'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE backtest_status AS ENUM ('pending', 'running', 'completed', 'failed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE signal_type AS ENUM ('entry_long', 'entry_short', 'exit_long', 'exit_short', 'rebalance'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            ENUM("admin", "trader", "analyst", "readonly", name="user_role", create_type=False),
            nullable=False,
            server_default="readonly",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    # Expression index for case-insensitive email lookup
    op.execute("CREATE UNIQUE INDEX ix_users_email_lower ON users (lower(email))")

    # ── strategies ────────────────────────────────────────────────────────
    op.create_table(
        "strategies",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("strategy_type", sa.String(50), nullable=False),
        sa.Column("parameters", JSONB()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_live", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("universe", JSONB()),
        sa.Column("risk_config", JSONB()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index(
        "ix_strategies_user_created",
        "strategies",
        ["user_id", sa.text("created_at DESC")],
    )

    # ── backtest_runs ─────────────────────────────────────────────────────
    op.create_table(
        "backtest_runs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column(
            "strategy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            ENUM("pending", "running", "completed", "failed", name="backtest_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("initial_capital_idr", sa.Numeric(30, 2), nullable=False),
        sa.Column("final_capital_idr", sa.Numeric(30, 2)),
        sa.Column("total_return_pct", sa.Numeric(10, 4)),
        sa.Column("cagr_pct", sa.Numeric(10, 4)),
        sa.Column("sharpe_ratio", sa.Numeric(10, 4)),
        sa.Column("sortino_ratio", sa.Numeric(10, 4)),
        sa.Column("calmar_ratio", sa.Numeric(10, 4)),
        sa.Column("max_drawdown_pct", sa.Numeric(10, 4)),
        sa.Column("max_drawdown_duration_days", sa.Integer()),
        sa.Column("total_trades", sa.Integer()),
        sa.Column("win_rate_pct", sa.Numeric(10, 4)),
        sa.Column("profit_factor", sa.Numeric(10, 4)),
        sa.Column("omega_ratio", sa.Numeric(10, 4)),
        sa.Column("parameters_snapshot", JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_backtest_runs_strategy", "backtest_runs", ["strategy_id"])
    op.create_index("ix_backtest_runs_user", "backtest_runs", ["user_id"])

    # ── signals (TimescaleDB hypertable) ──────────────────────────────────
    op.create_table(
        "signals",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "strategy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("instrument_symbol", sa.String(20), nullable=False),
        sa.Column(
            "signal_type",
            ENUM(
                "entry_long",
                "entry_short",
                "exit_long",
                "exit_short",
                "rebalance",
                name="signal_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Numeric(5, 4), nullable=False),
        sa.Column("bar_timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("acted_on", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resulting_order_id", sa.String(36)),
        sa.Column("metadata_json", JSONB()),
        sa.PrimaryKeyConstraint("id", "generated_at", name="pk_signals"),
    )
    op.create_index(
        "ix_signals_strategy_bar_ts",
        "signals",
        ["strategy_id", sa.text("bar_timestamp DESC")],
    )
    op.create_index(
        "ix_signals_instrument_generated",
        "signals",
        ["instrument_symbol", "generated_at"],
    )

    # CHECK constraints
    op.execute("ALTER TABLE signals ADD CONSTRAINT ck_signals_strength_range CHECK (strength BETWEEN -1.0 AND 1.0)")

    # Convert signals to TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable(
            'signals',
            'generated_at',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
    """)


def downgrade() -> None:
    """Drop tables in reverse dependency order, then enum types."""
    op.drop_table("signals")
    op.drop_table("backtest_runs")
    op.drop_table("strategies")
    op.execute("DROP INDEX IF EXISTS ix_users_email_lower")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS signal_type")
    op.execute("DROP TYPE IF EXISTS backtest_status")
    op.execute("DROP TYPE IF EXISTS user_role")
