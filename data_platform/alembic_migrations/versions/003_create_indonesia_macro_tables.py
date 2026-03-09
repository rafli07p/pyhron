"""Create Indonesia macroeconomic indicator tables.

Revision ID: 003
Create Date: 2024-01-01 00:02:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create macro indicator time series table."""
    op.create_table(
        "indonesia_macro_indicator",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("indicator_code", sa.String(100), nullable=False),
        sa.Column("indicator_name", sa.String(500), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("frequency", sa.String(30), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="macro",
    )
    op.create_index(
        "ix_macro_indicator_code_date",
        "indonesia_macro_indicator",
        ["indicator_code", "reference_date"],
        schema="macro",
        unique=True,
    )
    op.create_index(
        "ix_macro_indicator_source",
        "indonesia_macro_indicator",
        ["source"],
        schema="macro",
    )


def downgrade() -> None:
    """Drop macro indicator table."""
    op.drop_table("indonesia_macro_indicator", schema="macro")
