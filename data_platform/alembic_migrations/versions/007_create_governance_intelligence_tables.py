"""Create governance intelligence tables.

Revision ID: 007
Create Date: 2024-01-01 00:06:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create governance flag table for ownership changes, audit opinions."""
    op.create_table(
        "idx_equity_governance_flag",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("flag_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("filer_name", sa.String(500)),
        sa.Column("filer_type", sa.String(50)),
        sa.Column("shares_before", sa.BigInteger()),
        sa.Column("shares_after", sa.BigInteger()),
        sa.Column("change_pct", sa.Numeric(8, 4)),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("source_url", sa.String(2000)),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="governance",
    )
    op.create_index(
        "ix_governance_flag_symbol_date",
        "idx_equity_governance_flag",
        ["symbol", "event_date"],
        schema="governance",
    )
    op.create_index(
        "ix_governance_flag_type",
        "idx_equity_governance_flag",
        ["flag_type"],
        schema="governance",
    )
    op.create_index(
        "ix_governance_flag_severity",
        "idx_equity_governance_flag",
        ["severity"],
        schema="governance",
    )


def downgrade() -> None:
    """Drop governance flag table."""
    op.drop_table("idx_equity_governance_flag", schema="governance")
