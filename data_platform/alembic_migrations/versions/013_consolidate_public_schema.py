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
    ("market_data", "idx_equity_instrument", "instruments"),
    ("market_data", "idx_equity_ohlcv_tick", "ohlcv"),
    ("market_data", "idx_equity_financial_statement", "financial_statements"),
    ("market_data", "idx_equity_computed_ratio", "computed_ratios"),
    ("market_data", "idx_equity_corporate_action", "corporate_actions"),
    ("market_data", "idx_equity_index_constituent", "index_constituents"),
    ("market_data", "idx_equity_news_article", "news_articles"),
    # trading schema
    ("trading", "strategy_order_lifecycle_record", "orders"),
    ("trading", "strategy_position_current_snapshot", "positions"),
    ("trading", "strategy_trade_execution_log", "trade_executions"),
    # macro schema
    ("macro", "indonesia_macro_indicator", "macro_indicators"),
    # commodity schema
    ("commodity", "indonesia_commodity_daily_price", "commodity_prices"),
    # alternative_data schema
    ("alternative_data", "indonesia_fire_hotspot_event", "fire_hotspot_events"),
    ("alternative_data", "indonesia_weather_rainfall", "weather_rainfall"),
    # fixed_income schema
    ("fixed_income", "indonesia_government_bond_sbn", "government_bonds"),
    ("fixed_income", "indonesia_government_bond_yield_curve", "government_bond_yield_curve"),
    ("fixed_income", "indonesia_corporate_bond", "corporate_bonds"),
    # governance schema
    ("governance", "idx_equity_governance_flag", "governance_flags"),
]

# Tables already in public schema that need renaming to canonical short names
PUBLIC_RENAMES = [
    ("pyhron_user", "users"),
    ("pyhron_strategy", "strategies"),
    ("pyhron_backtest_run", "backtest_runs"),
    ("pyhron_signal", "signals"),
]


def upgrade() -> None:
    """Move all tables to public schema and rename to canonical names."""
    for old_schema, old_table, new_table in TABLE_MOVES:
        # Move table from source schema to public
        op.execute(f"ALTER TABLE IF EXISTS {old_schema}.{old_table} SET SCHEMA public")
        # Rename to canonical name (if different from the moved name)
        if old_table != new_table:
            op.execute(f"ALTER TABLE IF EXISTS public.{old_table} RENAME TO {new_table}")

    # Rename public-schema tables to canonical short names
    for old_name, new_name in PUBLIC_RENAMES:
        op.execute(f"ALTER TABLE IF EXISTS public.{old_name} RENAME TO {new_name}")


def downgrade() -> None:
    """Move tables back to their original schemas and restore original names."""
    # Restore public-schema table names
    for old_name, new_name in reversed(PUBLIC_RENAMES):
        op.execute(f"ALTER TABLE IF EXISTS public.{new_name} RENAME TO {old_name}")

    for old_schema, old_table, new_table in reversed(TABLE_MOVES):
        # Rename back to original name
        if old_table != new_table:
            op.execute(f"ALTER TABLE IF EXISTS public.{new_table} RENAME TO {old_table}")
        # Move back to original schema
        op.execute(f"ALTER TABLE IF EXISTS public.{old_table} SET SCHEMA {old_schema}")
