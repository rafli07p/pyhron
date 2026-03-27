"""Validate that the Pyhron database schema is correct after migrations.

Run after ``alembic upgrade head`` to verify all tables, indexes,
constraints, hypertables, and seed data are in place.

Usage::

    DATABASE_URL=postgresql+psycopg://... python scripts/validate_migrations.py
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, inspect, text

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required.")
    sys.exit(1)

# Convert async URL to sync if needed
sync_url = DATABASE_URL.replace("+asyncpg", "+psycopg").replace("+aiopg", "+psycopg")
engine = create_engine(sync_url)

# Expected schema artifacts
# After migration 013, ALL tables live in the public schema with canonical names.
EXPECTED_TABLES_BY_SCHEMA: dict[str, list[str]] = {
    "public": [
        # Market data (formerly market_data schema)
        "instruments",
        "ohlcv",
        "financial_statements",
        "computed_ratios",
        "corporate_actions",
        "index_constituents",
        "news_articles",
        # Trading (formerly trading schema)
        "orders",
        "positions",
        "trade_executions",
        # Macro (formerly macro schema)
        "macro_indicators",
        # Commodity (formerly commodity schema)
        "commodity_prices",
        # Alternative data (formerly alternative_data schema)
        "fire_hotspot_events",
        "weather_rainfall",
        # Fixed income (formerly fixed_income schema)
        "government_bonds",
        "government_bond_yield_curve",
        "corporate_bonds",
        # Governance (formerly governance schema)
        "governance_flags",
        # User/strategy/backtest/signal (always public)
        "users",
        "strategies",
        "backtest_runs",
        "signals",
        # Alembic
        "alembic_version",
    ],
}

EXPECTED_HYPERTABLES = ["ohlcv", "signals"]

EXPECTED_INDEXES: dict[str, list[str]] = {
    "public.instruments": ["ix_instruments_active_symbol"],
    "public.ohlcv": ["ix_ohlcv_brin_time"],
    "public.orders": ["ix_orders_open"],
    "public.users": ["ix_users_email_lower"],
    "public.signals": ["ix_signals_strategy_bar_ts", "ix_signals_instrument_generated"],
}

EXPECTED_CHECK_CONSTRAINTS: dict[str, list[str]] = {
    "public.ohlcv": [
        "ck_ohlcv_high_gte_low",
        "ck_ohlcv_volume_non_negative",
    ],
    "public.orders": ["ck_orders_filled_lte_quantity"],
    "public.positions": ["ck_positions_quantity_non_negative"],
    "public.signals": ["ck_signals_strength_range"],
}


def check_tables(conn) -> list[str]:
    """Verify all expected tables exist."""
    errors = []
    inspector = inspect(conn)
    for schema, tables in EXPECTED_TABLES_BY_SCHEMA.items():
        existing = set(inspector.get_table_names(schema=schema))
        for table in tables:
            if table not in existing:
                errors.append(f"Missing table: {schema}.{table}")
    total = sum(len(t) for t in EXPECTED_TABLES_BY_SCHEMA.values())
    if not errors:
        print(f"  [OK] All {total} expected tables present")
    return errors


def check_hypertables(conn) -> list[str]:
    """Verify TimescaleDB hypertables are configured.

    Skips gracefully when TimescaleDB is not installed (e.g. CI with plain postgres).
    """
    errors = []
    # Check if TimescaleDB extension is available before querying its catalog.
    has_timescale = conn.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
    ).scalar()
    if not has_timescale:
        print("  [SKIP] TimescaleDB not installed — hypertable check skipped")
        return errors

    result = conn.execute(text("SELECT hypertable_name FROM timescaledb_information.hypertables")).fetchall()
    existing = {r[0] for r in result}
    for table in EXPECTED_HYPERTABLES:
        if table not in existing:
            errors.append(f"Table '{table}' is not a TimescaleDB hypertable")
    if not errors:
        print(f"  [OK] TimescaleDB hypertables: {EXPECTED_HYPERTABLES}")
    return errors


def check_indexes(conn) -> list[str]:
    """Verify performance indexes exist."""
    errors = []
    inspector = inspect(conn)
    for qualified_table, expected_idxs in EXPECTED_INDEXES.items():
        schema, table = qualified_table.rsplit(".", 1)
        existing = {idx["name"] for idx in inspector.get_indexes(table, schema=schema)}
        for idx in expected_idxs:
            if idx not in existing:
                errors.append(f"Missing index {idx} on {qualified_table}")
    if not errors:
        print("  [OK] All performance indexes present")
    return errors


def check_check_constraints(conn) -> list[str]:
    """Verify CHECK constraints exist."""
    errors = []
    inspector = inspect(conn)
    for qualified_table, expected_cks in EXPECTED_CHECK_CONSTRAINTS.items():
        schema, table = qualified_table.rsplit(".", 1)
        existing = {ck["name"] for ck in inspector.get_check_constraints(table, schema=schema)}
        for ck in expected_cks:
            if ck not in existing:
                errors.append(f"Missing check constraint {ck} on {qualified_table}")
    if not errors:
        print("  [OK] All CHECK constraints present")
    return errors


def check_seed_data(conn) -> list[str]:
    """Verify LQ45 seed data is present."""
    errors = []
    count = conn.execute(text("SELECT COUNT(*) FROM instruments WHERE board = 'IDX'")).scalar()
    if count is None or count < 50:
        errors.append(f"Expected >= 50 IDX instruments, found {count}")
    ihsg = conn.execute(text("SELECT 1 FROM instruments WHERE symbol = '^JKSE'")).scalar()
    if not ihsg:
        errors.append("IHSG index (^JKSE) missing from instruments")
    if not errors:
        print(f"  [OK] Seed data: {count} IDX instruments including IHSG")
    return errors


def check_alembic_head(conn) -> list[str]:
    """Verify alembic version is recorded."""
    errors = []
    rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    if rev is None:
        errors.append("No alembic version recorded")
    else:
        print(f"  [OK] Alembic head: {rev}")
    return errors


def main() -> None:
    """Run all schema validation checks."""
    print("Running Pyhron schema validation...\n")
    all_errors: list[str] = []

    checks = [
        ("Tables", check_tables),
        ("Hypertables", check_hypertables),
        ("Indexes", check_indexes),
        ("Check Constraints", check_check_constraints),
        ("Seed Data", check_seed_data),
        ("Alembic Head", check_alembic_head),
    ]

    with engine.connect() as conn:
        for name, fn in checks:
            print(f"Checking {name}...")
            try:
                errors = fn(conn)
                for err in errors:
                    print(f"  [FAIL] {err}")
                all_errors.extend(errors)
            except Exception as exc:
                # Rollback the failed transaction so subsequent checks
                # are not blocked by InFailedSqlTransaction.
                conn.rollback()
                msg = f"{name}: {exc}"
                print(f"  [FAIL] {msg}")
                all_errors.append(msg)

    if all_errors:
        print(f"\n{len(all_errors)} validation(s) failed.")
        sys.exit(1)
    else:
        print("\n[OK] All validations passed. Schema is ready.")
        sys.exit(0)


if __name__ == "__main__":
    main()
