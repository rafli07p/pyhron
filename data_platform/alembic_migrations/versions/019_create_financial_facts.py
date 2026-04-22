"""Create financial_facts EAV table for IDX XBRL data.

Stores all XBRL-extracted financial metrics as (symbol, period,
context_type, metric) -> value key-value pairs, letting us persist
every tag in the taxonomy without schema churn.

Revision ID: 019
Revises: 018_ml_exec_portfolio
Create Date: 2026-04-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "019"
down_revision = "018_ml_exec_portfolio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_facts",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("context_type", sa.String(30), nullable=False),
        sa.Column("metric", sa.String(200), nullable=False),
        sa.Column("value", sa.Numeric(24, 2), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(50), server_default="idx_xbrl"),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_financial_facts_symbol_period",
        "financial_facts",
        ["symbol", "period"],
    )
    op.create_index(
        "ix_financial_facts_symbol_metric",
        "financial_facts",
        ["symbol", "metric"],
    )
    op.create_unique_constraint(
        "uq_financial_facts_symbol_period_context_metric",
        "financial_facts",
        ["symbol", "period", "context_type", "metric"],
    )


def downgrade() -> None:
    op.drop_table("financial_facts")
