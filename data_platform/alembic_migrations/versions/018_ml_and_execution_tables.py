"""018 - ML model runs, execution schedules, portfolio snapshots.

Revision ID: 018_ml_exec_portfolio
Revises: 017
Create Date: 2024-12-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "018_ml_exec_portfolio"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create schemas if not exists
    op.execute("CREATE SCHEMA IF NOT EXISTS ml")
    op.execute("CREATE SCHEMA IF NOT EXISTS trading")
    op.execute("CREATE SCHEMA IF NOT EXISTS portfolio")

    # ml.ml_model_runs: lightweight local index of MLflow runs
    op.create_table(
        "ml_model_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("mlflow_run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_names", JSONB, nullable=False),
        sa.Column("metrics", JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("false")),
        schema="ml",
    )
    op.create_index(
        "ix_ml_model_runs_name_registered",
        "ml_model_runs",
        ["model_name", sa.text("registered_at DESC")],
        schema="ml",
    )

    # trading.execution_schedules: persisted child order schedules
    op.create_table(
        "execution_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_order_id", UUID(as_uuid=True), nullable=False),
        sa.Column("algorithm", sa.String(32), nullable=False),
        sa.Column("parameters", JSONB, nullable=False),
        sa.Column("child_orders", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'completed', 'cancelled')",
            name="ck_execution_schedules_status",
        ),
        schema="trading",
    )

    # portfolio.portfolio_snapshots: historical weight records
    # Composite PK (id, snapshot_at) required — TimescaleDB needs the
    # partition column in every unique constraint on the hypertable.
    op.create_table(
        "portfolio_snapshots",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("weights", JSONB, nullable=False),
        sa.Column("expected_return", sa.Float, nullable=True),
        sa.Column("expected_vol", sa.Float, nullable=True),
        sa.Column("turnover", sa.Float, nullable=True),
        sa.Column("cost_bps", sa.Float, nullable=True),
        sa.PrimaryKeyConstraint("id", "snapshot_at", name="pk_portfolio_snapshots"),
        schema="portfolio",
    )

    # TimescaleDB hypertable for portfolio snapshots (if TimescaleDB is available)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                PERFORM create_hypertable('portfolio.portfolio_snapshots', 'snapshot_at', if_not_exists => TRUE);
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.drop_table("portfolio_snapshots", schema="portfolio")
    op.drop_table("execution_schedules", schema="trading")
    op.drop_index("ix_ml_model_runs_name_registered", table_name="ml_model_runs", schema="ml")
    op.drop_table("ml_model_runs", schema="ml")
