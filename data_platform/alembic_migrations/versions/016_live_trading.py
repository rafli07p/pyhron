"""Create live trading configuration, promotion audit, and portfolio risk snapshot tables.

Revision ID: 016
Revises: 015
Create Date: 2026-03-13 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Live trading configuration
    op.create_table(
        "live_trading_config",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "strategy_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("pyhron_strategy.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("max_position_size_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("10.00")),
        sa.Column("max_portfolio_var_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("5.00")),
        sa.Column("max_daily_loss_idr", sa.Numeric(20, 2), nullable=False),
        sa.Column("max_drawdown_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("15.00")),
        sa.Column("kill_switch_armed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("kill_switch_triggered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("kill_switch_reason", sa.Text(), nullable=True),
        sa.Column("kill_switch_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "promoted_from_session_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("pyhron_paper_trading_session.id"),
            nullable=True,
        ),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "promoted_by",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("pyhron_user.id"),
            nullable=True,
        ),
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
        sa.CheckConstraint("mode IN ('PAPER', 'LIVE')", name="ck_live_trading_config_mode"),
    )

    # Unique partial index: only one active config per strategy
    op.create_index(
        "ix_live_trading_config_strategy_active",
        "live_trading_config",
        ["strategy_id"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # Live promotion audit
    op.create_table(
        "live_promotion_audit",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "session_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("pyhron_paper_trading_session.id"),
            nullable=False,
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "checked_by",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("pyhron_user.id"),
            nullable=True,
        ),
        sa.Column("min_trading_days_met", sa.Boolean(), nullable=False),
        sa.Column("min_trades_met", sa.Boolean(), nullable=False),
        sa.Column("sharpe_threshold_met", sa.Boolean(), nullable=False),
        sa.Column("max_drawdown_met", sa.Boolean(), nullable=False),
        sa.Column("win_rate_met", sa.Boolean(), nullable=False),
        sa.Column("data_coverage_met", sa.Boolean(), nullable=False),
        sa.Column("overall_pass", sa.Boolean(), nullable=False),
        sa.Column("session_sharpe", sa.Numeric(8, 4), nullable=True),
        sa.Column("session_max_drawdown_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("session_win_rate_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("session_trading_days", sa.Integer(), nullable=True),
        sa.Column("session_total_trades", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_index(
        "ix_live_promotion_audit_session",
        "live_promotion_audit",
        ["session_id", "checked_at"],
    )

    # Portfolio risk snapshot (TimescaleDB hypertable)
    op.create_table(
        "portfolio_risk_snapshot",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "strategy_id",
            sa.dialects.postgresql.UUID(),
            sa.ForeignKey("pyhron_strategy.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("portfolio_var_1d_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("portfolio_var_5d_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("portfolio_beta", sa.Numeric(8, 4), nullable=True),
        sa.Column("sector_hhi", sa.Numeric(8, 4), nullable=True),
        sa.Column("gross_exposure_idr", sa.Numeric(20, 2), nullable=True),
        sa.Column("net_exposure_idr", sa.Numeric(20, 2), nullable=True),
        sa.Column("concentration_top5_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("largest_position_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("daily_loss_idr", sa.Numeric(20, 2), nullable=True),
        sa.Column("daily_loss_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", "timestamp"),
    )

    try:
        conn = op.get_bind()
        nested = conn.begin_nested()
        conn.execute(
            text(
                "SELECT create_hypertable('portfolio_risk_snapshot', 'timestamp', chunk_time_interval => INTERVAL '1 day')"
            )
        )
        nested.commit()
    except Exception:
        nested.rollback()

    op.create_index(
        "ix_portfolio_risk_snapshot_strategy",
        "portfolio_risk_snapshot",
        ["strategy_id", sa.text("timestamp DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_risk_snapshot_strategy", table_name="portfolio_risk_snapshot")
    op.drop_table("portfolio_risk_snapshot")
    op.drop_index("ix_live_promotion_audit_session", table_name="live_promotion_audit")
    op.drop_table("live_promotion_audit")
    op.drop_index("ix_live_trading_config_strategy_active", table_name="live_trading_config")
    op.drop_table("live_trading_config")
