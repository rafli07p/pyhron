"""Create fixed income tables: government bonds, corporate bonds.

Revision ID: 006
Create Date: 2024-01-01 00:05:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create government bond and corporate bond tables."""
    # Government bonds (SBN)
    op.create_table(
        "indonesia_government_bond_sbn",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("series_code", sa.String(30), nullable=False),
        sa.Column("instrument_type", sa.String(50), nullable=False),
        sa.Column("coupon_rate", sa.Numeric(6, 4)),
        sa.Column("maturity_date", sa.Date(), nullable=False),
        sa.Column("outstanding_amount_idr_bn", sa.Numeric(18, 4)),
        sa.Column("bid_yield", sa.Numeric(8, 4)),
        sa.Column("ask_yield", sa.Numeric(8, 4)),
        sa.Column("mid_yield", sa.Numeric(8, 4)),
        sa.Column("bid_price", sa.Numeric(12, 6)),
        sa.Column("ask_price", sa.Numeric(12, 6)),
        sa.Column("duration", sa.Numeric(8, 4)),
        sa.Column("modified_duration", sa.Numeric(8, 4)),
        sa.Column("convexity", sa.Numeric(10, 4)),
        sa.Column("daily_volume_idr_bn", sa.Numeric(18, 4)),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="fixed_income",
    )
    op.create_index(
        "ix_gov_bond_series_date",
        "indonesia_government_bond_sbn",
        ["series_code", "price_date"],
        schema="fixed_income",
        unique=True,
    )

    # Yield curve snapshots
    op.create_table(
        "indonesia_government_bond_yield_curve",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("curve_date", sa.Date(), nullable=False),
        sa.Column("tenor", sa.String(10), nullable=False),
        sa.Column("tenor_months", sa.Integer(), nullable=False),
        sa.Column("yield_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("change_bps", sa.Numeric(8, 4)),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="fixed_income",
    )
    op.create_index(
        "ix_yield_curve_date_tenor",
        "indonesia_government_bond_yield_curve",
        ["curve_date", "tenor_months"],
        schema="fixed_income",
        unique=True,
    )

    # Corporate bonds
    op.create_table(
        "indonesia_corporate_bond",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("isin", sa.String(12), nullable=False),
        sa.Column("issuer_name", sa.String(500), nullable=False),
        sa.Column("issuer_sector", sa.String(100)),
        sa.Column("coupon_rate", sa.Numeric(6, 4)),
        sa.Column("maturity_date", sa.Date(), nullable=False),
        sa.Column("outstanding_amount_idr_bn", sa.Numeric(18, 4)),
        sa.Column("rating_agency", sa.String(30)),
        sa.Column("credit_rating", sa.String(10)),
        sa.Column("rating_date", sa.Date()),
        sa.Column("yield_to_maturity", sa.Numeric(8, 4)),
        sa.Column("price", sa.Numeric(12, 6)),
        sa.Column("price_date", sa.Date()),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="fixed_income",
    )
    op.create_index(
        "ix_corp_bond_isin_date",
        "indonesia_corporate_bond",
        ["isin", "price_date"],
        schema="fixed_income",
    )


def downgrade() -> None:
    """Drop fixed income tables."""
    op.drop_table("indonesia_corporate_bond", schema="fixed_income")
    op.drop_table("indonesia_government_bond_yield_curve", schema="fixed_income")
    op.drop_table("indonesia_government_bond_sbn", schema="fixed_income")
