"""IDX Equity End-of-Day OHLCV ingestion.

Primary source: EODHD API (``/api/eod/{symbol}.IDX``)
Fallback source: yfinance (``{ticker}.JK``)

Design:
  - Idempotent upsert via INSERT ... ON CONFLICT DO UPDATE
  - IDX circuit breaker validation: reject single-day move > 35 %
  - OHLC sanity: high >= max(open, close), low <= min(open, close)
  - Rate limiting via Redis counter for EODHD free-tier (1 000 req/day)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import text

from shared.async_database_session import get_session
from shared.configuration_settings import get_config
from shared.platform_exception_hierarchy import (
    DataQualityError,
    IngestionError,
    RateLimitExceededError,
)
from shared.prometheus_metrics_registry import DATA_FRESHNESS, INGESTION_ROWS
from shared.redis_cache_client import get_redis
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# Constants
IDX_LQ45_SYMBOLS: list[str] = [
    "BBCA",
    "BBRI",
    "BMRI",
    "TLKM",
    "ASII",
    "UNVR",
    "GGRM",
    "HMSP",
    "BBNI",
    "ICBP",
    "INDF",
    "KLBF",
    "MDKA",
    "MNCN",
    "PGAS",
    "PTBA",
    "SMGR",
    "TBIG",
    "TOWR",
    "UNTR",
    "ADRO",
    "AMRT",
    "ANTM",
    "ARTO",
    "BFIN",
    "BRPT",
    "BUKA",
    "CPIN",
    "EMTK",
    "ERAA",
    "ESSA",
    "EXCL",
    "GOTO",
    "HRUM",
    "INCO",
    "INKP",
    "ITMG",
    "JPFA",
    "MAPI",
    "MBMA",
    "MEDC",
    "MIKA",
    "PGEO",
    "TKIM",
    "TPIA",
]

EODHD_RATE_LIMIT_KEY = "pyhron:eodhd:daily_requests"
EODHD_DAILY_LIMIT = 1000
MAX_DAILY_MOVE_PCT = 0.35
MAX_RETRIES = 3


@dataclass
class IngestionResult:
    """Outcome of an ingestion run."""

    source: str
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    gaps_detected: list[date] = field(default_factory=list)
    duration_ms: float = 0.0


class IDXEquityEODIngester:
    """IDX end-of-day OHLCV ingester with EODHD primary, yfinance fallback.

    Usage::

        ingester = IDXEquityEODIngester()
        result = await ingester.ingest_for_date_range(
            symbol="BBCA",
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )
    """

    def __init__(self) -> None:
        self._config = get_config()
        self._logger = get_logger(__name__)
        self._eodhd_key: str = self._config.eodhd_api_key

    # ── Public API ───────────────────────────────────────────────────────

    async def ingest_for_date_range(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> IngestionResult:
        """Ingest EOD OHLCV data for *symbol* over [start, end].

        Args:
            symbol: IDX ticker (e.g. ``"BBCA"``).
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="eodhd")

        try:
            rows = await self._fetch_eodhd(symbol, start, end)
            result.source = "eodhd"
        except (IngestionError, RateLimitExceededError):
            self._logger.warning("eodhd_fallback", symbol=symbol)
            try:
                rows = await self._fetch_yfinance(symbol, start, end)
                result.source = "yfinance"
            except Exception as exc:
                result.errors.append(f"Both sources failed: {exc}")
                result.duration_ms = (time.monotonic() - t0) * 1000
                return result

        valid_rows: list[dict[str, Any]] = []
        for row in rows:
            try:
                self._validate_ohlc(row)
                valid_rows.append(row)
            except DataQualityError as exc:
                result.errors.append(str(exc))
                result.rows_skipped += 1

        inserted, updated = await self._upsert_rows(symbol, valid_rows)
        result.rows_inserted = inserted
        result.rows_updated = updated
        result.gaps_detected = await self._detect_gaps(symbol, start, end)
        result.duration_ms = (time.monotonic() - t0) * 1000

        INGESTION_ROWS.labels(source=result.source, symbol=symbol, operation="inserted").inc(inserted)
        INGESTION_ROWS.labels(source=result.source, symbol=symbol, operation="updated").inc(updated)
        DATA_FRESHNESS.labels(symbol=symbol).set(0)

        self._logger.info(
            "eod_ingestion_complete",
            symbol=symbol,
            source=result.source,
            rows_inserted=inserted,
            rows_updated=updated,
            gaps=len(result.gaps_detected),
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    async def ingest_batch(
        self,
        symbols: list[str] | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[IngestionResult]:
        """Ingest EOD data for a list of symbols (default: LQ45).

        Args:
            symbols: Tickers to ingest; defaults to ``IDX_LQ45_SYMBOLS``.
            start: First calendar date; defaults to ``2020-01-01``.
            end: Last calendar date; defaults to today.

        Returns:
            One ``IngestionResult`` per symbol.
        """
        target = symbols or IDX_LQ45_SYMBOLS
        start = start or date(2020, 1, 1)
        end = end or date.today()
        results: list[IngestionResult] = []
        for sym in target:
            result = await self.ingest_for_date_range(sym, start, end)
            results.append(result)
        return results

    # ── Data sources ─────────────────────────────────────────────────────

    async def _fetch_eodhd(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch from EODHD API with rate limiting and retry."""
        if not self._eodhd_key:
            raise IngestionError("EODHD API key not configured")

        redis = await get_redis()
        count = await redis.incr(EODHD_RATE_LIMIT_KEY)
        if count == 1:
            await redis.expire(EODHD_RATE_LIMIT_KEY, 86400)
        if count > EODHD_DAILY_LIMIT:
            raise RateLimitExceededError(f"EODHD daily limit ({EODHD_DAILY_LIMIT}) exceeded")

        url = f"https://eodhd.com/api/eod/{symbol}.IDX"
        params = {
            "api_token": self._eodhd_key,
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "period": "d",
            "fmt": "json",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 429:
                        raise RateLimitExceededError("EODHD rate limit hit (HTTP 429)")
                    resp.raise_for_status()
                    data = resp.json()
                    return [
                        {
                            "time": row["date"],
                            "open": Decimal(str(row["open"])),
                            "high": Decimal(str(row["high"])),
                            "low": Decimal(str(row["low"])),
                            "close": Decimal(str(row["close"])),
                            "adjusted_close": Decimal(str(row.get("adjusted_close", row["close"]))),
                            "volume": int(row["volume"]),
                        }
                        for row in data
                    ]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (429, 500, 502, 503) and attempt < MAX_RETRIES:
                    wait = 1 * (2 ** (attempt - 1))
                    self._logger.warning("eodhd_retry", attempt=attempt, wait_s=wait)
                    await asyncio.sleep(wait)
                    continue
                raise IngestionError(f"EODHD API error: {exc}") from exc
            except httpx.RequestError as exc:
                raise IngestionError(f"EODHD connection error: {exc}") from exc

        raise IngestionError(f"EODHD failed after {MAX_RETRIES} attempts")

    async def _fetch_yfinance(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch from yfinance as fallback source."""

        def _sync_yfinance_fetch() -> list[dict[str, Any]]:
            import yfinance as yf

            ticker = yf.Ticker(f"{symbol}.JK")
            hist = ticker.history(
                start=start_date.isoformat(),
                end=end_date.isoformat(),
            )
            sync_rows: list[dict[str, Any]] = []
            for ts, row in hist.iterrows():
                sync_rows.append(
                    {
                        "time": ts.strftime("%Y-%m-%d"),
                        "open": Decimal(str(round(row["Open"], 6))),
                        "high": Decimal(str(round(row["High"], 6))),
                        "low": Decimal(str(round(row["Low"], 6))),
                        "close": Decimal(str(round(row["Close"], 6))),
                        "adjusted_close": Decimal(str(round(row["Close"], 6))),
                        "volume": int(row["Volume"]),
                    }
                )
            return sync_rows

        return await asyncio.to_thread(_sync_yfinance_fetch)

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_ohlc(self, row: dict[str, Any]) -> None:
        """Validate OHLC sanity constraints.

        Raises:
            DataQualityError: If any constraint is violated.
        """
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        if h < max(o, c):
            raise DataQualityError(f"High {h} < max(open={o}, close={c}) on {row['time']}")
        if l > min(o, c):
            raise DataQualityError(f"Low {l} > min(open={o}, close={c}) on {row['time']}")
        if o <= 0 or c <= 0:
            raise DataQualityError(f"Non-positive price on {row['time']}")

        if o > 0:
            daily_move = abs(float(c - o) / float(o))
            if daily_move > MAX_DAILY_MOVE_PCT:
                raise DataQualityError(
                    f"Daily move {daily_move:.1%} exceeds IDX circuit breaker {MAX_DAILY_MOVE_PCT:.0%} on {row['time']}"
                )

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_rows(
        self,
        symbol: str,
        rows: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert OHLCV rows into ``market_ticks``.

        Returns:
            Tuple of (inserted, updated) counts.
        """
        if not rows:
            return 0, 0

        inserted = 0
        updated = 0

        async with get_session() as session:
            for row in rows:
                result = await session.execute(
                    text("""
                        INSERT INTO market_ticks
                            (time, symbol, exchange, open, high, low, close, volume, adjusted_close)
                        VALUES
                            (:time, :symbol, 'IDX', :open, :high, :low, :close, :volume, :adjusted_close)
                        ON CONFLICT (time, symbol, exchange) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            adjusted_close = EXCLUDED.adjusted_close
                        RETURNING (xmax = 0) AS is_insert
                    """),
                    {
                        "time": f"{row['time']}T00:00:00+07:00",
                        "symbol": symbol,
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": row["volume"],
                        "adjusted_close": float(row["adjusted_close"]),
                    },
                )
                is_insert = result.scalar()
                if is_insert:
                    inserted += 1
                else:
                    updated += 1

        return inserted, updated

    async def _detect_gaps(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
    ) -> list[date]:
        """Detect missing trading days for *symbol* between two dates.

        Returns:
            List of missing trading-day dates.
        """
        async with get_session() as session:
            result = await session.execute(
                text("""
                    SELECT d::date AS trading_day
                    FROM generate_series(:from_date::date, :to_date::date, '1 day') d
                    WHERE EXTRACT(DOW FROM d) NOT IN (0, 6)
                      AND d::date NOT IN (
                          SELECT time::date FROM market_ticks
                          WHERE symbol = :symbol AND exchange = 'IDX'
                            AND time::date BETWEEN :from_date AND :to_date
                      )
                    ORDER BY d
                """),
                {"symbol": symbol, "from_date": from_date, "to_date": to_date},
            )
            return [row[0] for row in result.fetchall()]
