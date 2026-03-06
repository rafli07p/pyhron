"""
Historical storage engine for the Enthropy data platform.

SQLAlchemy models for PostgreSQL with date-based partitioning for
OHLCV bars, trade records, and corporate actions.  Provides an async
engine for storing and querying large historical datasets.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

import structlog
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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
# ORM Models
# ---------------------------------------------------------------------------

class OHLCVRecord(Base):
    """OHLCV bar record – partitioned by ``bar_date`` in PostgreSQL.

    The table uses declarative column mapping.  Actual range partitioning
    is applied via raw DDL in :pymethod:`HistoricalStorageEngine._ensure_partitions`.
    """

    __tablename__ = "ohlcv_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "symbol", "bar_date", "timeframe", name="uq_ohlcv_bar"),
        Index("ix_ohlcv_symbol_date", "tenant_id", "symbol", "bar_date"),
        {"postgresql_partition_by": "RANGE (bar_date)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    bar_date: Mapped[date] = mapped_column(Date, nullable=False, primary_key=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False, default="1d")  # 1m, 5m, 1h, 1d
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    vwap: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    trade_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="polygon")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class TradeRecord(Base):
    """Individual trade record – partitioned by ``trade_date``."""

    __tablename__ = "trade_records"
    __table_args__ = (
        Index("ix_trade_symbol_date", "tenant_id", "symbol", "trade_date"),
        {"postgresql_partition_by": "RANGE (trade_date)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=True)
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trade_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="polygon")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class CorporateAction(Base):
    """Corporate action record (dividends, splits, mergers)."""

    __tablename__ = "corporate_actions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "symbol", "action_type", "ex_date", name="uq_corp_action"),
        Index("ix_corp_action_symbol", "tenant_id", "symbol", "ex_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)  # dividend, split, merger
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    record_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)  # split ratio
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)  # dividend amount
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="polygon")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# HistoricalStorageEngine
# ---------------------------------------------------------------------------

class HistoricalStorageEngine:
    """Async engine for storing and querying historical market data.

    Parameters
    ----------
    database_url : str
        Async SQLAlchemy connection string
        (e.g. ``postgresql+asyncpg://user:pass@host/db``).
    tenant_id : str
        Tenant identifier for multi-tenancy isolation.
    echo : bool
        When ``True`` SQLAlchemy logs all emitted SQL.
    """

    def __init__(
        self,
        database_url: str = "postgresql+asyncpg://localhost/enthropy",
        tenant_id: str = "default",
        echo: bool = False,
    ) -> None:
        self.tenant_id = tenant_id
        self._log = logger.bind(tenant_id=tenant_id, component="HistoricalStorageEngine")
        self._engine = create_async_engine(
            database_url,
            echo=echo,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        self._log.info("historical_engine_initialised", url=database_url)

    async def init_schema(self) -> None:
        """Create tables (non-partitioned flavour) if they don't exist."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self._log.info("schema_initialised")

    async def close(self) -> None:
        await self._engine.dispose()
        self._log.info("engine_disposed")

    # ------------------------------------------------------------------
    # Partition management
    # ------------------------------------------------------------------

    async def ensure_partitions(self, start_year: int, end_year: int) -> list[str]:
        """Create monthly range partitions for OHLCV and trade tables.

        Returns the list of partition names created.
        """
        created: list[str] = []
        async with self._engine.begin() as conn:
            for year in range(start_year, end_year + 1):
                for month in range(1, 13):
                    next_month = month + 1
                    next_year = year
                    if next_month > 12:
                        next_month = 1
                        next_year = year + 1

                    for table in ("ohlcv_records", "trade_records"):
                        part_name = f"{table}_y{year}m{month:02d}"
                        from_val = f"{year}-{month:02d}-01"
                        to_val = f"{next_year}-{next_month:02d}-01"
                        ddl = text(
                            f"CREATE TABLE IF NOT EXISTS {part_name} "
                            f"PARTITION OF {table} "
                            f"FOR VALUES FROM ('{from_val}') TO ('{to_val}')"
                        )
                        try:
                            await conn.execute(ddl)
                            created.append(part_name)
                        except Exception:
                            self._log.debug("partition_exists", name=part_name)
        self._log.info("partitions_ensured", count=len(created), range=f"{start_year}-{end_year}")
        return created

    async def partition_management(
        self, *, retain_months: int = 24
    ) -> dict[str, list[str]]:
        """Drop partitions older than *retain_months* and ensure upcoming ones exist.

        Returns dict with ``created`` and ``dropped`` partition names.
        """
        now = datetime.now(timezone.utc)
        current_year = now.year
        current_month = now.month

        # Ensure 12 months ahead
        end_year = current_year + 1
        created = await self.ensure_partitions(current_year, end_year)

        # Identify partitions to drop
        dropped: list[str] = []
        cutoff_year = current_year - (retain_months // 12)
        cutoff_month = current_month - (retain_months % 12)
        if cutoff_month <= 0:
            cutoff_month += 12
            cutoff_year -= 1

        async with self._engine.begin() as conn:
            for table in ("ohlcv_records", "trade_records"):
                for year in range(cutoff_year - 2, cutoff_year + 1):
                    for month in range(1, 13):
                        if year < cutoff_year or (year == cutoff_year and month < cutoff_month):
                            part_name = f"{table}_y{year}m{month:02d}"
                            try:
                                await conn.execute(text(f"DROP TABLE IF EXISTS {part_name}"))
                                dropped.append(part_name)
                            except Exception:
                                pass

        self._log.info("partition_management_complete", created=len(created), dropped=len(dropped))
        return {"created": created, "dropped": dropped}

    # ------------------------------------------------------------------
    # Store bars
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.3, max=5),
        retry=retry_if_exception_type((OSError, ConnectionError)),
        reraise=True,
    )
    async def store_bars(
        self,
        bars: Sequence[dict],
        *,
        timeframe: str = "1d",
        source: str = "polygon",
    ) -> int:
        """Upsert OHLCV bars.

        Each dict in *bars* must have at minimum:
        ``symbol``, ``bar_date`` (or ``date``), ``open``, ``high``,
        ``low``, ``close``, ``volume``.

        Returns the number of records upserted.
        """
        async with self._session_factory() as session:
            async with session.begin():
                count = 0
                for bar in bars:
                    bar_date = bar.get("bar_date") or bar.get("date")
                    if isinstance(bar_date, str):
                        bar_date = date.fromisoformat(bar_date)

                    record = OHLCVRecord(
                        tenant_id=self.tenant_id,
                        symbol=bar["symbol"].upper(),
                        bar_date=bar_date,
                        timeframe=timeframe,
                        open=Decimal(str(bar["open"])),
                        high=Decimal(str(bar["high"])),
                        low=Decimal(str(bar["low"])),
                        close=Decimal(str(bar["close"])),
                        volume=int(bar.get("volume", 0)),
                        vwap=Decimal(str(bar["vwap"])) if bar.get("vwap") else None,
                        trade_count=bar.get("trade_count") or bar.get("transactions"),
                        source=source,
                    )
                    session.add(record)
                    count += 1

        self._log.info("bars_stored", count=count, timeframe=timeframe, source=source)
        return count

    # ------------------------------------------------------------------
    # Query bars
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.3, max=5),
        retry=retry_if_exception_type((OSError, ConnectionError)),
        reraise=True,
    )
    async def query_bars(
        self,
        symbol: str,
        *,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        timeframe: str = "1d",
        limit: int = 10_000,
    ) -> list[dict]:
        """Query OHLCV bars for *symbol* within a date range.

        Returns a list of dicts with bar data, ordered by ``bar_date`` ASC.
        """
        from sqlalchemy import select

        stmt = (
            select(OHLCVRecord)
            .where(OHLCVRecord.tenant_id == self.tenant_id)
            .where(OHLCVRecord.symbol == symbol.upper())
            .where(OHLCVRecord.timeframe == timeframe)
        )

        if start_date:
            stmt = stmt.where(OHLCVRecord.bar_date >= start_date)
        if end_date:
            stmt = stmt.where(OHLCVRecord.bar_date <= end_date)

        stmt = stmt.order_by(OHLCVRecord.bar_date.asc()).limit(limit)

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        bars = [
            {
                "symbol": r.symbol,
                "bar_date": r.bar_date.isoformat(),
                "timeframe": r.timeframe,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": r.volume,
                "vwap": float(r.vwap) if r.vwap else None,
                "trade_count": r.trade_count,
                "source": r.source,
            }
            for r in rows
        ]

        self._log.debug("bars_queried", symbol=symbol, count=len(bars))
        return bars

    # ------------------------------------------------------------------
    # Store trades
    # ------------------------------------------------------------------

    async def store_trades(self, trades: Sequence[dict], *, source: str = "polygon") -> int:
        """Bulk-insert trade records.  Returns count stored."""
        async with self._session_factory() as session:
            async with session.begin():
                count = 0
                for t in trades:
                    ts = t.get("timestamp") or t.get("sip_timestamp") or t.get("t")
                    if isinstance(ts, (int, float)):
                        ts = datetime.fromtimestamp(ts / 1e9 if ts > 1e12 else ts, tz=timezone.utc)
                    elif isinstance(ts, str):
                        ts = datetime.fromisoformat(ts)

                    trade_date = ts.date() if isinstance(ts, datetime) else date.today()

                    record = TradeRecord(
                        tenant_id=self.tenant_id,
                        symbol=t["symbol"].upper(),
                        trade_date=trade_date,
                        timestamp=ts,
                        price=Decimal(str(t["price"])),
                        size=int(t.get("size", 0)),
                        exchange=t.get("exchange", ""),
                        conditions=",".join(str(c) for c in t.get("conditions", [])),
                        trade_id=t.get("trade_id") or t.get("id"),
                        source=source,
                    )
                    session.add(record)
                    count += 1

        self._log.info("trades_stored", count=count, source=source)
        return count


__all__ = [
    "Base",
    "OHLCVRecord",
    "TradeRecord",
    "CorporateAction",
    "HistoricalStorageEngine",
]
