#!/usr/bin/env python3
"""
Database setup script for the Pyhron Trading Platform.

Creates database tables, runs Alembic migrations, and sets up initial
schema including indices, partitions, and extensions.

Usage:
    python scripts/setup_db.py                    # Full setup
    python scripts/setup_db.py --migrate-only     # Run migrations only
    python scripts/setup_db.py --reset            # Drop and recreate all tables
    python scripts/setup_db.py --check            # Check migration status
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pyhron.setup_db")

# =============================================================================
# Configuration
# =============================================================================
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. Example: postgresql+asyncpg://user:pass@localhost:5432/dbname"
    )
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

REQUIRED_EXTENSIONS = [
    "uuid-ossp",
    "pg_stat_statements",
    "btree_gist",
]

# =============================================================================
# SQL Statements
# =============================================================================
CREATE_EXTENSIONS_SQL = """
DO $$
BEGIN
    {extensions}
END
$$;
"""

CREATE_SCHEMAS_SQL = """
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS risk;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS analytics;
"""

CREATE_ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS trading.orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_order_id VARCHAR(64) UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type VARCHAR(12) NOT NULL CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    quantity DECIMAL(20, 8) NOT NULL CHECK (quantity > 0),
    price DECIMAL(20, 8),
    filled_quantity DECIMAL(20, 8) DEFAULT 0,
    average_fill_price DECIMAL(20, 8),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'partially_filled', 'filled', 'cancelled', 'rejected', 'risk_rejected', 'expired')),
    strategy_id VARCHAR(64) NOT NULL,
    exchange VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_limit_price CHECK (
        (order_type IN ('limit', 'stop_limit') AND price IS NOT NULL)
        OR order_type IN ('market', 'stop')
    )
);

CREATE INDEX IF NOT EXISTS idx_orders_symbol ON trading.orders (symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON trading.orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_strategy ON trading.orders (strategy_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON trading.orders (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_symbol_status ON trading.orders (symbol, status);
"""

CREATE_FILLS_TABLE = """
CREATE TABLE IF NOT EXISTS trading.fills (
    fill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES trading.orders(order_id),
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(4) NOT NULL CHECK (direction IN ('buy', 'sell')),
    quantity DECIMAL(20, 8) NOT NULL CHECK (quantity > 0),
    price DECIMAL(20, 8) NOT NULL CHECK (price > 0),
    commission DECIMAL(20, 8) NOT NULL DEFAULT 0,
    venue VARCHAR(20),
    fill_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    strategy_id VARCHAR(64) NOT NULL,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_fills_order_id ON trading.fills (order_id);
CREATE INDEX IF NOT EXISTS idx_fills_symbol ON trading.fills (symbol);
CREATE INDEX IF NOT EXISTS idx_fills_timestamp ON trading.fills (fill_timestamp DESC);
"""

CREATE_POSITIONS_TABLE = """
CREATE TABLE IF NOT EXISTS trading.positions (
    position_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    average_entry_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 8),
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    market_value DECIMAL(20, 8),
    strategy_id VARCHAR(64) NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_symbol_strategy UNIQUE (symbol, strategy_id)
);

CREATE INDEX IF NOT EXISTS idx_positions_strategy ON trading.positions (strategy_id);
"""

CREATE_TICK_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS market_data.ticks (
    tick_id BIGSERIAL,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    volume BIGINT NOT NULL DEFAULT 0,
    bid DECIMAL(20, 8),
    ask DECIMAL(20, 8),
    exchange VARCHAR(20),
    timestamp TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tick_id, timestamp)
) PARTITION BY RANGE (timestamp);

CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON market_data.ticks (symbol, timestamp DESC);
"""

CREATE_PNL_TABLE = """
CREATE TABLE IF NOT EXISTS analytics.daily_pnl (
    pnl_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_date DATE NOT NULL,
    strategy_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(20),
    gross_pnl DECIMAL(20, 8) NOT NULL,
    net_pnl DECIMAL(20, 8) NOT NULL,
    total_commissions DECIMAL(20, 8) NOT NULL DEFAULT 0,
    trade_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_daily_pnl UNIQUE (report_date, strategy_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_daily_pnl_date ON analytics.daily_pnl (report_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_pnl_strategy ON analytics.daily_pnl (strategy_id);
"""

CREATE_RISK_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS risk.snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    portfolio_value DECIMAL(20, 8) NOT NULL,
    total_exposure DECIMAL(20, 8) NOT NULL,
    current_var DECIMAL(20, 8),
    drawdown_pct DECIMAL(10, 6),
    leverage DECIMAL(10, 4),
    position_count INTEGER NOT NULL DEFAULT 0,
    violations JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_risk_snapshots_time ON risk.snapshots (snapshot_time DESC);
"""

CREATE_AUDIT_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS audit.logs (
    log_id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(64),
    actor VARCHAR(64),
    action VARCHAR(50) NOT NULL,
    details JSONB DEFAULT '{}',
    ip_address INET,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit.logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit.logs (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit.logs (actor);
"""

CREATE_UPDATED_AT_TRIGGER = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'trading.orders',
            'trading.positions'
        ])
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS set_updated_at ON %s; '
            'CREATE TRIGGER set_updated_at BEFORE UPDATE ON %s '
            'FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();',
            tbl, tbl
        );
    END LOOP;
END
$$;
"""


# =============================================================================
# Setup Functions
# =============================================================================
async def create_extensions(engine: AsyncEngine) -> None:
    """Create required PostgreSQL extensions."""
    logger.info("Creating PostgreSQL extensions...")
    ext_statements = "\n".join(f'    CREATE EXTENSION IF NOT EXISTS "{ext}";' for ext in REQUIRED_EXTENSIONS)
    sql = CREATE_EXTENSIONS_SQL.format(extensions=ext_statements)

    async with engine.begin() as conn:
        await conn.execute(text(sql))
    logger.info(f"Extensions created: {', '.join(REQUIRED_EXTENSIONS)}")


async def create_schemas(engine: AsyncEngine) -> None:
    """Create database schemas."""
    logger.info("Creating schemas...")
    async with engine.begin() as conn:
        await conn.execute(text(CREATE_SCHEMAS_SQL))
    logger.info("Schemas created: trading, market_data, risk, audit, analytics")


async def create_tables(engine: AsyncEngine) -> None:
    """Create all database tables."""
    logger.info("Creating tables...")
    tables = [
        ("trading.orders", CREATE_ORDERS_TABLE),
        ("trading.fills", CREATE_FILLS_TABLE),
        ("trading.positions", CREATE_POSITIONS_TABLE),
        ("market_data.ticks", CREATE_TICK_DATA_TABLE),
        ("analytics.daily_pnl", CREATE_PNL_TABLE),
        ("risk.snapshots", CREATE_RISK_SNAPSHOTS_TABLE),
        ("audit.logs", CREATE_AUDIT_LOG_TABLE),
    ]

    async with engine.begin() as conn:
        for table_name, ddl in tables:
            logger.info(f"  Creating {table_name}...")
            await conn.execute(text(ddl))

    logger.info(f"Created {len(tables)} tables.")


async def create_triggers(engine: AsyncEngine) -> None:
    """Create database triggers."""
    logger.info("Creating triggers...")
    async with engine.begin() as conn:
        await conn.execute(text(CREATE_UPDATED_AT_TRIGGER))
    logger.info("Triggers created.")


async def create_tick_partitions(engine: AsyncEngine, year: int = 2024) -> None:
    """Create monthly partitions for tick data."""
    logger.info(f"Creating tick data partitions for {year}...")
    async with engine.begin() as conn:
        for month in range(1, 13):
            next_month = month + 1
            next_year = year
            if next_month > 12:
                next_month = 1
                next_year = year + 1

            partition_name = f"ticks_{year}_{month:02d}"
            sql = f"""
            CREATE TABLE IF NOT EXISTS market_data.{partition_name}
            PARTITION OF market_data.ticks
            FOR VALUES FROM ('{year}-{month:02d}-01')
            TO ('{next_year}-{next_month:02d}-01');
            """
            await conn.execute(text(sql))
            logger.info(f"  Created partition: {partition_name}")


def run_migrations() -> None:
    """Run Alembic migrations."""
    logger.info("Running Alembic migrations...")
    alembic_cfg = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations complete.")


def check_migration_status() -> None:
    """Check current migration status."""
    logger.info("Checking migration status...")
    alembic_cfg = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)
    command.current(alembic_cfg, verbose=True)


async def reset_database(engine: AsyncEngine) -> None:
    """Drop and recreate all tables. DESTRUCTIVE OPERATION."""
    logger.warning("RESETTING DATABASE - All data will be lost!")

    schemas = ["trading", "market_data", "risk", "audit", "analytics"]
    async with engine.begin() as conn:
        for schema in schemas:
            logger.info(f"  Dropping schema {schema}...")
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))

    logger.info("All schemas dropped. Recreating...")


async def verify_setup(engine: AsyncEngine) -> bool:
    """Verify database setup is correct."""
    logger.info("Verifying database setup...")
    checks_passed = True

    async with engine.begin() as conn:
        # Check extensions
        result = await conn.execute(text("SELECT extname FROM pg_extension"))
        extensions = {row[0] for row in result.fetchall()}
        for ext in REQUIRED_EXTENSIONS:
            if ext in extensions:
                logger.info(f"  [OK] Extension: {ext}")
            else:
                logger.error(f"  [FAIL] Extension missing: {ext}")
                checks_passed = False

        # Check tables
        result = await conn.execute(
            text("""
            SELECT schemaname || '.' || tablename
            FROM pg_tables
            WHERE schemaname IN ('trading', 'market_data', 'risk', 'audit', 'analytics')
            ORDER BY schemaname, tablename
        """)
        )
        tables = [row[0] for row in result.fetchall()]
        logger.info(f"  Found {len(tables)} tables: {', '.join(tables)}")

    return checks_passed


# =============================================================================
# Main
# =============================================================================
async def full_setup() -> None:
    """Run complete database setup."""
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        await create_extensions(engine)
        await create_schemas(engine)
        await create_tables(engine)
        await create_triggers(engine)
        await create_tick_partitions(engine, year=2024)
        await create_tick_partitions(engine, year=2025)

        success = await verify_setup(engine)
        if success:
            logger.info("Database setup completed successfully.")
        else:
            logger.error("Database setup completed with errors.")
            sys.exit(1)

    finally:
        await engine.dispose()


def main() -> None:
    """Entry point for the setup script."""
    parser = argparse.ArgumentParser(description="Pyhron Database Setup")
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help="Run Alembic migrations only",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables (DESTRUCTIVE)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check current migration status",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify database setup",
    )
    args = parser.parse_args()

    if args.check:
        check_migration_status()
        return

    if args.migrate_only:
        run_migrations()
        return

    if args.reset:
        confirm = input("This will DELETE ALL DATA. Type 'yes-delete-everything' to confirm: ")
        if confirm != "yes-delete-everything":
            logger.info("Reset cancelled.")
            return
        engine = create_async_engine(DATABASE_URL, echo=False)
        asyncio.run(reset_database(engine))

    if args.verify:
        engine = create_async_engine(DATABASE_URL, echo=False)
        asyncio.run(verify_setup(engine))
        return

    asyncio.run(full_setup())

    # Run Alembic migrations after table creation
    try:
        run_migrations()
    except Exception as e:
        logger.warning(f"Alembic migrations skipped: {e}")
        logger.info("This is expected if alembic.ini is not configured yet.")


if __name__ == "__main__":
    main()
