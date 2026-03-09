"""Create Indonesia commodity price tables.

Revision ID: 004
Create Date: 2024-01-01 00:03:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create commodity daily price table."""
    op.create_table(
        "indonesia_commodity_daily_price",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("commodity_code", sa.String(30), nullable=False),
        sa.Column("commodity_name", sa.String(200), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("previous_price", sa.Numeric(18, 6)),
        sa.Column("change_pct", sa.Numeric(8, 4)),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="commodity",
    )
    op.create_index(
        "ix_commodity_code_date",
        "indonesia_commodity_daily_price",
        ["commodity_code", "price_date"],
        schema="commodity",
        unique=True,
    )


def downgrade() -> None:
    """Drop commodity price table."""
    op.drop_table("indonesia_commodity_daily_price", schema="commodity")
