"""Create commodity_company_profiles table and seed initial data.

Revision ID: 017
Revises: 016
Create Date: 2026-03-25 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commodity_company_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("commodity_type", sa.String(20), nullable=False),
        sa.Column("profile_data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("shares_outstanding", sa.BigInteger, nullable=False),
        sa.Column("trailing_revenue_idr", sa.Float, nullable=False),
        sa.Column("net_margin", sa.Float, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("ticker", "commodity_type", name="uq_commodity_profile_ticker_type"),
    )
    op.create_index("ix_commodity_profiles_type", "commodity_company_profiles", ["commodity_type"])

    # Seed initial profiles from previously hardcoded data
    profiles = sa.table(
        "commodity_company_profiles",
        sa.column("ticker", sa.String),
        sa.column("commodity_type", sa.String),
        sa.column("profile_data", JSONB),
        sa.column("shares_outstanding", sa.BigInteger),
        sa.column("trailing_revenue_idr", sa.Float),
        sa.column("net_margin", sa.Float),
    )

    op.bulk_insert(
        profiles,
        [
            # Coal miners
            {
                "ticker": "ADRO",
                "commodity_type": "coal",
                "shares_outstanding": 31_985_962_000,
                "trailing_revenue_idr": 82e12,
                "net_margin": 0.28,
                "profile_data": {
                    "annual_production_mt": 60.0,
                    "avg_calorie_kcal": 4200,
                    "cash_cost_usd_per_ton": 38.0,
                    "royalty_rate": 0.135,
                    "strip_ratio": 5.2,
                    "dmo_pct": 0.25,
                    "dmo_cap_usd": 90.0,
                },
            },
            {
                "ticker": "PTBA",
                "commodity_type": "coal",
                "shares_outstanding": 2_304_131_850,
                "trailing_revenue_idr": 36e12,
                "net_margin": 0.25,
                "profile_data": {
                    "annual_production_mt": 30.0,
                    "avg_calorie_kcal": 5400,
                    "cash_cost_usd_per_ton": 42.0,
                    "royalty_rate": 0.135,
                    "strip_ratio": 4.8,
                    "dmo_pct": 0.25,
                    "dmo_cap_usd": 90.0,
                },
            },
            {
                "ticker": "ITMG",
                "commodity_type": "coal",
                "shares_outstanding": 1_129_925_000,
                "trailing_revenue_idr": 42e12,
                "net_margin": 0.22,
                "profile_data": {
                    "annual_production_mt": 20.0,
                    "avg_calorie_kcal": 5800,
                    "cash_cost_usd_per_ton": 45.0,
                    "royalty_rate": 0.14,
                    "strip_ratio": 6.0,
                    "dmo_pct": 0.25,
                    "dmo_cap_usd": 90.0,
                },
            },
            {
                "ticker": "BUMI",
                "commodity_type": "coal",
                "shares_outstanding": 20_773_400_000,
                "trailing_revenue_idr": 60e12,
                "net_margin": 0.12,
                "profile_data": {
                    "annual_production_mt": 80.0,
                    "avg_calorie_kcal": 4000,
                    "cash_cost_usd_per_ton": 50.0,
                    "royalty_rate": 0.135,
                    "strip_ratio": 7.0,
                    "dmo_pct": 0.25,
                    "dmo_cap_usd": 90.0,
                },
            },
            {
                "ticker": "HRUM",
                "commodity_type": "coal",
                "shares_outstanding": 2_703_620_000,
                "trailing_revenue_idr": 12e12,
                "net_margin": 0.18,
                "profile_data": {
                    "annual_production_mt": 8.0,
                    "avg_calorie_kcal": 4800,
                    "cash_cost_usd_per_ton": 35.0,
                    "royalty_rate": 0.135,
                    "strip_ratio": 4.0,
                    "dmo_pct": 0.25,
                    "dmo_cap_usd": 90.0,
                },
            },
            # CPO (palm oil) plantation companies
            {
                "ticker": "AALI",
                "commodity_type": "cpo",
                "shares_outstanding": 1_574_745_000,
                "trailing_revenue_idr": 22e12,
                "net_margin": 0.12,
                "profile_data": {
                    "plantation_area_ha": 280_000,
                    "ffb_yield_ton_per_ha": 18.0,
                    "oer_pct": 0.22,
                    "hedging_ratio": 0.20,
                    "downstream_refining": False,
                    "dmo_allocation_pct": 0.0,
                },
            },
            {
                "ticker": "LSIP",
                "commodity_type": "cpo",
                "shares_outstanding": 6_822_863_965,
                "trailing_revenue_idr": 7e12,
                "net_margin": 0.15,
                "profile_data": {
                    "plantation_area_ha": 95_000,
                    "ffb_yield_ton_per_ha": 17.5,
                    "oer_pct": 0.23,
                    "hedging_ratio": 0.15,
                    "downstream_refining": False,
                    "dmo_allocation_pct": 0.0,
                },
            },
            {
                "ticker": "SIMP",
                "commodity_type": "cpo",
                "shares_outstanding": 15_816_310_000,
                "trailing_revenue_idr": 16e12,
                "net_margin": 0.08,
                "profile_data": {
                    "plantation_area_ha": 260_000,
                    "ffb_yield_ton_per_ha": 16.0,
                    "oer_pct": 0.21,
                    "hedging_ratio": 0.10,
                    "downstream_refining": True,
                    "dmo_allocation_pct": 0.30,
                },
            },
            {
                "ticker": "TBLA",
                "commodity_type": "cpo",
                "shares_outstanding": 5_342_098_939,
                "trailing_revenue_idr": 11e12,
                "net_margin": 0.10,
                "profile_data": {
                    "plantation_area_ha": 150_000,
                    "ffb_yield_ton_per_ha": 17.0,
                    "oer_pct": 0.22,
                    "hedging_ratio": 0.05,
                    "downstream_refining": True,
                    "dmo_allocation_pct": 0.20,
                },
            },
            {
                "ticker": "BWPT",
                "commodity_type": "cpo",
                "shares_outstanding": 7_799_040_000,
                "trailing_revenue_idr": 4.5e12,
                "net_margin": 0.06,
                "profile_data": {
                    "plantation_area_ha": 60_000,
                    "ffb_yield_ton_per_ha": 15.0,
                    "oer_pct": 0.20,
                    "hedging_ratio": 0.0,
                    "downstream_refining": False,
                    "dmo_allocation_pct": 0.0,
                },
            },
            {
                "ticker": "SSMS",
                "commodity_type": "cpo",
                "shares_outstanding": 9_525_000_000,
                "trailing_revenue_idr": 6e12,
                "net_margin": 0.14,
                "profile_data": {
                    "plantation_area_ha": 100_000,
                    "ffb_yield_ton_per_ha": 19.0,
                    "oer_pct": 0.23,
                    "hedging_ratio": 0.10,
                    "downstream_refining": False,
                    "dmo_allocation_pct": 0.0,
                },
            },
            {
                "ticker": "PALM",
                "commodity_type": "cpo",
                "shares_outstanding": 8_124_850_000,
                "trailing_revenue_idr": 3e12,
                "net_margin": 0.05,
                "profile_data": {
                    "plantation_area_ha": 40_000,
                    "ffb_yield_ton_per_ha": 14.0,
                    "oer_pct": 0.20,
                    "hedging_ratio": 0.0,
                    "downstream_refining": False,
                    "dmo_allocation_pct": 0.0,
                },
            },
            # Nickel producers
            {
                "ticker": "INCO",
                "commodity_type": "nickel",
                "shares_outstanding": 9_936_338_720,
                "trailing_revenue_idr": 18e12,
                "net_margin": 0.20,
                "profile_data": {
                    "nickel_production_ton": 72_000,
                    "product_type": "nickel_matte",
                    "lme_correlation": 0.85,
                    "nickel_revenue_share": 0.95,
                    "cash_cost_usd_per_ton": 8000,
                    "royalty_rate": 0.10,
                },
            },
            {
                "ticker": "ANTM",
                "commodity_type": "nickel",
                "shares_outstanding": 24_030_764_725,
                "trailing_revenue_idr": 50e12,
                "net_margin": 0.10,
                "profile_data": {
                    "nickel_production_ton": 25_000,
                    "product_type": "ferronickel",
                    "lme_correlation": 0.75,
                    "nickel_revenue_share": 0.40,
                    "cash_cost_usd_per_ton": 10000,
                    "royalty_rate": 0.10,
                },
            },
            {
                "ticker": "MDKA",
                "commodity_type": "nickel",
                "shares_outstanding": 21_897_053_200,
                "trailing_revenue_idr": 12e12,
                "net_margin": 0.15,
                "profile_data": {
                    "nickel_production_ton": 15_000,
                    "product_type": "mixed_hydroxide_precipitate",
                    "lme_correlation": 0.70,
                    "nickel_revenue_share": 0.60,
                    "cash_cost_usd_per_ton": 9000,
                    "royalty_rate": 0.10,
                },
            },
            # Energy (ICP crude)
            {
                "ticker": "PGAS",
                "commodity_type": "energy",
                "shares_outstanding": 24_241_508_196,
                "trailing_revenue_idr": 55e12,
                "net_margin": 0.08,
                "profile_data": {
                    "oil_production_bopd": 0,
                    "gas_production_boepd": 400_000,
                    "oil_price_sensitivity": 0.15,
                    "gas_oil_price_linkage": 0.60,
                    "cost_recovery_pct": 0.0,
                    "government_take_pct": 0.0,
                },
            },
            {
                "ticker": "MEDC",
                "commodity_type": "energy",
                "shares_outstanding": 3_332_451_450,
                "trailing_revenue_idr": 18e12,
                "net_margin": 0.15,
                "profile_data": {
                    "oil_production_bopd": 25_000,
                    "gas_production_boepd": 50_000,
                    "oil_price_sensitivity": 0.80,
                    "gas_oil_price_linkage": 0.55,
                    "cost_recovery_pct": 0.40,
                    "government_take_pct": 0.55,
                },
            },
            {
                "ticker": "ENRG",
                "commodity_type": "energy",
                "shares_outstanding": 47_149_000_000,
                "trailing_revenue_idr": 8e12,
                "net_margin": 0.05,
                "profile_data": {
                    "oil_production_bopd": 10_000,
                    "gas_production_boepd": 30_000,
                    "oil_price_sensitivity": 0.70,
                    "gas_oil_price_linkage": 0.50,
                    "cost_recovery_pct": 0.35,
                    "government_take_pct": 0.60,
                },
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_commodity_profiles_type", table_name="commodity_company_profiles")
    op.drop_table("commodity_company_profiles")
