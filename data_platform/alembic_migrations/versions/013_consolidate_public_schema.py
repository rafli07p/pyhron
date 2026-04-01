"""Consolidate all tables into public schema with canonical names.

Moves tables from market_data, trading, macro, commodity, alternative_data,
fixed_income, and governance schemas into the public schema, renaming them
to short canonical names matching the ORM model __tablename__ declarations.

Revision ID: 013
Create Date: 2026-03-11 00:00:00.000000
"""

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

# (old_schema, old_table, new_table)
TABLE_MOVES = [
    # market_data schema
    ("market_data", "idx_equity_instrument", "idx_equity_instrument"),
    ("market_data", "idx_equity_ohlcv_tick", "idx_equity_ohlcv_tick"),
    ("market_data", "idx_equity_financial_statement", "idx_equity_financial_statement"),
    ("market_data", "idx_equity_computed_ratio", "idx_equity_computed_ratio"),
    ("market_data", "idx_equity_corporate_action", "idx_equity_corporate_action"),
    ("market_data", "idx_equity_index_constituent", "idx_equity_index_constituent"),
    ("market_data", "idx_equity_news_article", "idx_equity_news_article"),
    # trading schema
    ("trading", "strategy_order_lifecycle_record", "pyhron_order_lifecycle_record"),
    ("trading", "strategy_position_current_snapshot", "pyhron_strategy_position_snapshot"),
    ("trading", "strategy_trade_execution_log", "pyhron_strategy_trade_execution_log"),
    # macro schema
    ("macro", "indonesia_macro_indicator", "idn_macro_indicator"),
    # commodity schema
    ("commodity", "indonesia_commodity_daily_price", "idn_commodity_price"),
    # alternative_data schema
    ("alternative_data", "indonesia_fire_hotspot_event", "idn_fire_hotspot_event"),
    ("alternative_data", "indonesia_weather_rainfall", "idn_weather_rainfall"),
    # fixed_income schema
    ("fixed_income", "indonesia_government_bond_sbn", "idn_government_bond"),
    ("fixed_income", "indonesia_government_bond_yield_curve", "government_bond_yield_curve"),
    ("fixed_income", "indonesia_corporate_bond", "idn_corporate_bond"),
    # governance schema
    ("governance", "idx_equity_governance_flag", "idx_equity_governance_flag"),
]


def upgrade() -> None:
    """Move all tables to public schema and rename to canonical names."""
    for old_schema, old_table, new_table in TABLE_MOVES:
        # Move table from source schema to public
        op.execute(f"ALTER TABLE IF EXISTS {old_schema}.{old_table} SET SCHEMA public")
        # Rename to canonical name (if different from the moved name)
        if old_table != new_table:
            op.execute(f"ALTER TABLE IF EXISTS public.{old_table} RENAME TO {new_table}")

    # Drop now-empty schemas (they still exist but are empty)
    # Keep them around — they can be dropped manually if desired


def downgrade() -> None:
    """Move tables back to their original schemas and restore original names."""
    for old_schema, old_table, new_table in reversed(TABLE_MOVES):
        # Rename back to original name
        if old_table != new_table:
            op.execute(f"ALTER TABLE IF EXISTS public.{new_table} RENAME TO {old_table}")
        # Move back to original schema
        op.execute(f"ALTER TABLE IF EXISTS public.{old_table} SET SCHEMA {old_schema}")
