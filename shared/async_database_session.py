"""Async SQLAlchemy engine and session management.

Usage::

    from shared.async_database_session import get_engine, get_session, Base

    async with get_session() as session:
        result = await session.execute(select(Instrument))
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from shared.configuration_settings import get_config

# Naming convention for constraints (Alembic auto-generation friendly)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Create and cache the async SQLAlchemy engine."""
    config = get_config()
    return create_async_engine(
        config.database_url,
        pool_size=config.database_pool_size,
        max_overflow=config.database_max_overflow,
        pool_timeout=config.database_pool_timeout,
        echo=config.app_debug,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create and cache the session factory."""
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async session with automatic rollback on exception."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
