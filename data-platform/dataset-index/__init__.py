"""
Dataset index for the Enthropy data platform.

Provides a searchable catalog of available datasets with metadata
(source, time range, symbols, quality score).  Backed by SQLAlchemy/
PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional, Sequence

import structlog
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
    text,
    or_,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class DatasetMetadata(Base):
    """Catalog entry for a registered dataset."""

    __tablename__ = "dataset_index"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_dataset_name"),
        Index("ix_dataset_source", "tenant_id", "source"),
        Index("ix_dataset_quality", "quality_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)  # polygon, yfinance, internal
    asset_class: Mapped[str] = mapped_column(String(32), nullable=False, default="equity")
    symbols: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, default="1d")
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    record_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
        onupdate=datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "asset_class": self.asset_class,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "record_count": self.record_count,
            "quality_score": self.quality_score,
            "tags": self.tags,
            "extra_metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# DatasetIndex
# ---------------------------------------------------------------------------

class DatasetIndex:
    """Searchable catalog of available datasets.

    Parameters
    ----------
    database_url : str
        Async SQLAlchemy connection string.
    tenant_id : str
        Tenant identifier for multi-tenancy isolation.
    """

    def __init__(
        self,
        database_url: str = "postgresql+asyncpg://localhost/enthropy",
        tenant_id: str = "default",
        echo: bool = False,
    ) -> None:
        self.tenant_id = tenant_id
        self._log = logger.bind(tenant_id=tenant_id, component="DatasetIndex")
        self._engine = create_async_engine(
            database_url, echo=echo, pool_size=5, max_overflow=10, pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        self._log.info("dataset_index_initialised")

    async def init_schema(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self._log.info("schema_initialised")

    async def close(self) -> None:
        await self._engine.dispose()

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.3, max=5),
        retry=retry_if_exception_type((OSError, ConnectionError)),
        reraise=True,
    )
    async def register_dataset(
        self,
        name: str,
        source: str,
        *,
        description: Optional[str] = None,
        asset_class: str = "equity",
        symbols: Optional[list[str]] = None,
        timeframe: str = "1d",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        record_count: Optional[int] = None,
        quality_score: float = 1.0,
        tags: Optional[list[str]] = None,
        extra_metadata: Optional[dict] = None,
    ) -> dict:
        """Register (or update) a dataset in the catalog.

        Returns the dataset dict.
        """
        async with self._session_factory() as session:
            async with session.begin():
                # Check if dataset already exists for this tenant
                stmt = (
                    select(DatasetMetadata)
                    .where(DatasetMetadata.tenant_id == self.tenant_id)
                    .where(DatasetMetadata.name == name)
                )
                existing = (await session.execute(stmt)).scalar_one_or_none()

                if existing:
                    existing.source = source
                    existing.description = description or existing.description
                    existing.asset_class = asset_class
                    existing.symbols = symbols or existing.symbols
                    existing.timeframe = timeframe
                    existing.start_date = start_date or existing.start_date
                    existing.end_date = end_date or existing.end_date
                    existing.record_count = record_count if record_count is not None else existing.record_count
                    existing.quality_score = quality_score
                    existing.tags = tags or existing.tags
                    existing.extra_metadata = extra_metadata or existing.extra_metadata
                    existing.updated_at = datetime.now(timezone.utc)
                    dataset = existing
                    self._log.info("dataset_updated", name=name)
                else:
                    dataset = DatasetMetadata(
                        tenant_id=self.tenant_id,
                        name=name,
                        description=description,
                        source=source,
                        asset_class=asset_class,
                        symbols=symbols,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date,
                        record_count=record_count,
                        quality_score=quality_score,
                        tags=tags,
                        extra_metadata=extra_metadata,
                    )
                    session.add(dataset)
                    self._log.info("dataset_registered", name=name, source=source)

                await session.flush()
                return dataset.to_dict()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_datasets(
        self,
        *,
        query: Optional[str] = None,
        source: Optional[str] = None,
        asset_class: Optional[str] = None,
        symbol: Optional[str] = None,
        min_quality: Optional[float] = None,
        tags: Optional[list[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Search datasets with flexible filtering.

        Parameters
        ----------
        query : str | None
            Free-text search against name and description.
        source : str | None
            Filter by data source.
        asset_class : str | None
            Filter by asset class.
        symbol : str | None
            Filter datasets that contain this symbol.
        min_quality : float | None
            Minimum quality score.
        tags : list[str] | None
            Filter datasets having ANY of these tags.
        limit / offset : int
            Pagination.
        """
        stmt = (
            select(DatasetMetadata)
            .where(DatasetMetadata.tenant_id == self.tenant_id)
        )

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    DatasetMetadata.name.ilike(pattern),
                    DatasetMetadata.description.ilike(pattern),
                )
            )
        if source:
            stmt = stmt.where(DatasetMetadata.source == source)
        if asset_class:
            stmt = stmt.where(DatasetMetadata.asset_class == asset_class)
        if symbol:
            stmt = stmt.where(DatasetMetadata.symbols.any(symbol.upper()))
        if min_quality is not None:
            stmt = stmt.where(DatasetMetadata.quality_score >= min_quality)
        if tags:
            stmt = stmt.where(DatasetMetadata.tags.overlap(tags))

        stmt = (
            stmt.order_by(DatasetMetadata.quality_score.desc(), DatasetMetadata.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        datasets = [r.to_dict() for r in rows]
        self._log.debug("datasets_searched", count=len(datasets), query=query)
        return datasets

    # ------------------------------------------------------------------
    # Get info
    # ------------------------------------------------------------------

    async def get_dataset_info(self, name: str) -> Optional[dict]:
        """Get full metadata for a single dataset by name."""
        stmt = (
            select(DatasetMetadata)
            .where(DatasetMetadata.tenant_id == self.tenant_id)
            .where(DatasetMetadata.name == name)
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return row.to_dict()

    async def get_dataset_by_id(self, dataset_id: str | uuid.UUID) -> Optional[dict]:
        """Get full metadata for a single dataset by ID."""
        if isinstance(dataset_id, str):
            dataset_id = uuid.UUID(dataset_id)
        stmt = (
            select(DatasetMetadata)
            .where(DatasetMetadata.id == dataset_id)
            .where(DatasetMetadata.tenant_id == self.tenant_id)
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return row.to_dict() if row else None

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_dataset(self, name: str) -> bool:
        """Remove a dataset from the catalog.  Returns ``True`` if found."""
        from sqlalchemy import delete as sa_delete

        stmt = (
            sa_delete(DatasetMetadata)
            .where(DatasetMetadata.tenant_id == self.tenant_id)
            .where(DatasetMetadata.name == name)
        )
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(stmt)
                deleted = result.rowcount > 0

        if deleted:
            self._log.info("dataset_deleted", name=name)
        return deleted

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def dataset_count(self) -> int:
        """Return the total number of datasets for this tenant."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(DatasetMetadata)
            .where(DatasetMetadata.tenant_id == self.tenant_id)
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return result.scalar_one()


__all__ = [
    "DatasetMetadata",
    "DatasetIndex",
]
