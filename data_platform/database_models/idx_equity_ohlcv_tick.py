"""IDX equity OHLCV tick data (TimescaleDB hypertable).

Stores intraday and daily price/volume bars for all IDX-listed equities.
Designed as a TimescaleDB hypertable partitioned by time in 7-day chunks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Index, Numeric, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


class IdxEquityOhlcvTick(Base):
    """TimescaleDB hypertable for OHLCV tick data.

    Partitioned by time (7-day chunks).  Composite primary key on
    ``(time, symbol, exchange)``.

    Attributes:
        time: Observation timestamp.
        symbol: Ticker symbol.
        exchange: Exchange mic code.
        open: Opening price.
        high: Highest price.
        low: Lowest price.
        close: Closing price.
        volume: Traded volume (shares).
        vwap: Volume-weighted average price.
        bid: Best bid price.
        ask: Best ask price.
        adjusted_close: Split/dividend-adjusted close.
    """

    __tablename__ = "idx_equity_ohlcv_ticks"

    time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), primary_key=True, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=True)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=True)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=True)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    bid: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    ask: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)

    __table_args__ = (
        Index("ix_idx_equity_ohlcv_ticks_symbol_time", "symbol", time.desc()),
        Index(
            "ix_idx_equity_ohlcv_ticks_exchange_symbol_time",
            "exchange",
            "symbol",
            time.desc(),
        ),
    )
