"""Alembic environment configuration for Pyhron data platform.

Supports both online (async) and offline migration modes.
Imports all database models to ensure Alembic detects table changes.
"""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from shared.async_database_session import Base

# Import all models so Alembic sees them for autogenerate
import data_platform.models.market  # noqa: F401
import data_platform.models.trading  # noqa: F401

target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from environment or configuration_settings."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        from shared.configuration_settings import get_config
        return get_config().database_url
    except ImportError:
        return "postgresql+asyncpg://pyhron:pyhron@postgres:5432/pyhron"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode for SQL script generation."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Execute migrations against a live database connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    engine = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
