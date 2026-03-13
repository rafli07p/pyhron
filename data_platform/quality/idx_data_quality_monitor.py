"""Data quality monitoring for IDX data ingestion.

Computes data quality metrics after each ingestion batch.
Results are persisted to DB and logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy import text

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from strategy_engine.idx_trading_calendar import is_trading_day

logger = get_logger(__name__)


@dataclass
class CoverageReport:
    trade_date: date
    total_active_instruments: int
    instruments_with_data: int
    coverage_pct: float
    missing_symbols: list[str]
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class PriceSpikeAlert:
    symbol: str
    trade_date: date
    daily_return_pct: float
    z_score: float
    prev_close: Decimal
    close: Decimal


class IDXDataQualityMonitor:
    """Computes data quality metrics after each ingestion batch."""

    async def compute_coverage(
        self,
        trade_date: date,
        db_session: AsyncSession,
    ) -> CoverageReport:
        """Check what fraction of active instruments have OHLCV bar for trade_date.

        Alert if coverage_pct < 0.95.
        """
        # Get all active instruments
        active_result = await db_session.execute(text("SELECT symbol FROM instruments WHERE is_active = TRUE"))
        active_symbols = {row[0] for row in active_result.fetchall()}

        if not active_symbols:
            return CoverageReport(
                trade_date=trade_date,
                total_active_instruments=0,
                instruments_with_data=0,
                coverage_pct=1.0,
                missing_symbols=[],
            )

        # Get symbols with data for this date
        data_result = await db_session.execute(
            text("SELECT DISTINCT symbol FROM ohlcv " "WHERE time::date = :trade_date"),
            {"trade_date": trade_date.isoformat()},
        )
        symbols_with_data = {row[0] for row in data_result.fetchall()}

        missing = sorted(active_symbols - symbols_with_data)
        coverage_pct = len(symbols_with_data & active_symbols) / len(active_symbols) if active_symbols else 1.0

        report = CoverageReport(
            trade_date=trade_date,
            total_active_instruments=len(active_symbols),
            instruments_with_data=len(symbols_with_data & active_symbols),
            coverage_pct=coverage_pct,
            missing_symbols=missing,
        )

        if coverage_pct < 0.95:
            logger.warning(
                "low_data_coverage",
                trade_date=str(trade_date),
                coverage_pct=f"{coverage_pct:.2%}",
                missing_count=len(missing),
                missing_sample=missing[:10],
            )

        return report

    async def detect_gaps(
        self,
        symbol: str,
        lookback_days: int = 10,
        db_session: AsyncSession | None = None,
    ) -> list[date]:
        """Identify missing trading days in recent OHLCV history."""
        if db_session is None:
            return []

        from datetime import timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days + 10)  # Extra buffer for weekends

        # Get actual data dates
        result = await db_session.execute(
            text(
                "SELECT DISTINCT time::date as trade_date FROM ohlcv "
                "WHERE symbol = :symbol AND time::date >= :start_date AND time::date <= :end_date "
                "ORDER BY trade_date"
            ),
            {"symbol": symbol, "start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        )
        actual_dates = {row[0] for row in result.fetchall()}

        # Generate expected trading days
        expected_dates: list[date] = []
        current = start_date
        while current <= end_date:
            if is_trading_day(current):
                expected_dates.append(current)
            current += timedelta(days=1)

        # Only check the last lookback_days trading days
        expected_dates = expected_dates[-lookback_days:]
        return [d for d in expected_dates if d not in actual_dates]

    async def detect_price_spikes(
        self,
        trade_date: date,
        db_session: AsyncSession,
        z_score_threshold: float = 5.0,
    ) -> list[PriceSpikeAlert]:
        """Identify suspicious price movements using rolling z-score."""
        result = await db_session.execute(
            text(
                "WITH recent AS ("
                "  SELECT symbol, time::date as trade_date, close, "
                "    LAG(close) OVER (PARTITION BY symbol ORDER BY time) as prev_close "
                "  FROM ohlcv WHERE time::date >= :start_date AND time::date <= :trade_date"
                ") "
                "SELECT symbol, trade_date, close, prev_close "
                "FROM recent WHERE trade_date = :trade_date AND prev_close IS NOT NULL"
            ),
            {
                "trade_date": trade_date.isoformat(),
                "start_date": (trade_date - __import__("datetime").timedelta(days=60)).isoformat(),
            },
        )

        alerts: list[PriceSpikeAlert] = []
        rows = result.fetchall()

        # Compute returns and z-scores
        returns = []
        row_data = []
        for row in rows:
            sym, td, close, prev_close = row
            if prev_close and float(prev_close) > 0:
                ret = (float(close) - float(prev_close)) / float(prev_close)
                returns.append(ret)
                row_data.append((sym, td, close, prev_close, ret))

        if len(returns) < 2:
            return alerts

        mean_ret = float(np.mean(returns))
        std_ret = float(np.std(returns))
        if std_ret == 0:
            return alerts

        for sym, td, close, prev_close, ret in row_data:
            z = abs((ret - mean_ret) / std_ret)
            if z > z_score_threshold:
                alerts.append(
                    PriceSpikeAlert(
                        symbol=sym,
                        trade_date=td,
                        daily_return_pct=ret * 100,
                        z_score=z,
                        prev_close=Decimal(str(prev_close)),
                        close=Decimal(str(close)),
                    )
                )

        return alerts

    async def compute_completeness_score(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
        db_session: AsyncSession,
    ) -> float:
        """Returns fraction of expected trading days that have OHLCV data."""
        from datetime import timedelta

        # Count expected trading days
        expected = 0
        current = date_from
        while current <= date_to:
            if is_trading_day(current):
                expected += 1
            current += timedelta(days=1)

        if expected == 0:
            return 1.0

        # Count actual data
        result = await db_session.execute(
            text(
                "SELECT COUNT(DISTINCT time::date) FROM ohlcv "
                "WHERE symbol = :symbol AND time::date >= :date_from AND time::date <= :date_to"
            ),
            {"symbol": symbol, "date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        )
        actual = result.scalar() or 0
        return float(actual) / expected
