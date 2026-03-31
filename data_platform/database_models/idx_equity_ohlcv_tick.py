"""IDX equity OHLCV tick data.

Stores daily price/volume bars for all IDX-listed equities.
Column names match the canonical schema after migration 013.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Index, Numeric, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base


class IdxEquityOhlcvTick(Base):
    """OHLCV price data table.

    Composite primary key on ``(time, symbol, exchange)``.
    """

    __tablename__ = "ohlcv"

    time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False, default="IDX")
    interval: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")
    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    close: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    ingested_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    __table_args__ = (
        Index("ix_ohlcv_symbol_time", "symbol", time.desc()),
    )
