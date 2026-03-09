"""IDX Equity Fundamental (quarterly financials) ingestion.

Source: EODHD Fundamentals API (``/api/fundamentals/{symbol}.IDX``)

Design:
  - Fetches income statement, balance sheet, and cash flow per quarter
  - Validates key accounting identities (e.g. assets = liabilities + equity)
  - Idempotent upsert keyed on (symbol, fiscal_date, statement_type)
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

from shared.configuration_settings import get_config
from shared.async_database_session import get_session
from shared.redis_cache_client import get_redis
from shared.platform_exception_hierarchy import (
    DataQualityError,
    IngestionError,
    RateLimitExceededError,
)
from shared.structured_json_logger import get_logger
from shared.prometheus_metrics_registry import INGESTION_ROWS

logger = get_logger(__name__)

EODHD_RATE_LIMIT_KEY = "pyhron:eodhd:daily_requests"
EODHD_DAILY_LIMIT = 1000
MAX_RETRIES = 3


@dataclass
class IngestionResult:
    """Outcome of an ingestion run."""

    source: str
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class IDXEquityFundamentalIngester:
    """Quarterly financial-statement ingester from EODHD Fundamentals API.

    Fetches income statement, balance sheet and cash-flow statement for each
    symbol and upserts into the ``equity_fundamentals`` table.

    Usage::

        ingester = IDXEquityFundamentalIngester()
        result = await ingester.ingest_for_date_range(
            symbol="BBCA",
            start=date(2023, 1, 1),
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
        """Ingest quarterly fundamentals for *symbol* over [start, end].

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
            raw = await self._fetch_fundamentals(symbol)
        except (IngestionError, RateLimitExceededError) as exc:
            result.errors.append(str(exc))
            result.duration_ms = (time.monotonic() - t0) * 1000
            return result

        statements = self._extract_quarterly_statements(raw, start, end)

        valid: list[dict[str, Any]] = []
        for stmt in statements:
            try:
                self._validate_statement(stmt)
                valid.append(stmt)
            except DataQualityError as exc:
                result.errors.append(str(exc))
                result.rows_skipped += 1

        inserted, updated = await self._upsert_statements(symbol, valid)
        result.rows_inserted = inserted
        result.rows_updated = updated
        result.duration_ms = (time.monotonic() - t0) * 1000

        INGESTION_ROWS.labels(
            source="eodhd", symbol=symbol, operation="inserted"
        ).inc(inserted)
        INGESTION_ROWS.labels(
            source="eodhd", symbol=symbol, operation="updated"
        ).inc(updated)

        self._logger.info(
            "fundamental_ingestion_complete",
            symbol=symbol,
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    async def ingest_batch(
        self,
        symbols: list[str],
        start: date,
        end: date,
    ) -> list[IngestionResult]:
        """Ingest fundamentals for multiple symbols sequentially.

        Args:
            symbols: List of IDX tickers.
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            One ``IngestionResult`` per symbol.
        """
        results: list[IngestionResult] = []
        for sym in symbols:
            result = await self.ingest_for_date_range(sym, start, end)
            results.append(result)
        return results

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_fundamentals(self, symbol: str) -> dict[str, Any]:
        """Fetch full fundamentals JSON from EODHD.

        Raises:
            IngestionError: On API or network failure.
            RateLimitExceededError: When daily limit exceeded.
        """
        if not self._eodhd_key:
            raise IngestionError("EODHD API key not configured")

        redis = await get_redis()
        count = await redis.incr(EODHD_RATE_LIMIT_KEY)
        if count == 1:
            await redis.expire(EODHD_RATE_LIMIT_KEY, 86400)
        if count > EODHD_DAILY_LIMIT:
            raise RateLimitExceededError(
                f"EODHD daily limit ({EODHD_DAILY_LIMIT}) exceeded"
            )

        url = f"https://eodhd.com/api/fundamentals/{symbol}.IDX"
        params = {"api_token": self._eodhd_key, "fmt": "json"}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 429:
                        raise RateLimitExceededError("EODHD rate limit (HTTP 429)")
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (429, 500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"EODHD fundamentals error: {exc}") from exc
            except httpx.RequestError as exc:
                raise IngestionError(f"EODHD connection error: {exc}") from exc

        raise IngestionError(f"EODHD fundamentals failed after {MAX_RETRIES} retries")

    # ── Parsing ──────────────────────────────────────────────────────────

    def _extract_quarterly_statements(
        self,
        raw: dict[str, Any],
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse quarterly income/balance/cashflow from EODHD response.

        Args:
            raw: Full EODHD fundamentals JSON.
            start: Filter start date.
            end: Filter end date.

        Returns:
            List of normalised statement dicts.
        """
        statements: list[dict[str, Any]] = []
        financials = raw.get("Financials", {})

        for stmt_type, section_key in [
            ("income_statement", "Income_Statement"),
            ("balance_sheet", "Balance_Sheet"),
            ("cash_flow", "Cash_Flow"),
        ]:
            section = financials.get(section_key, {}).get("quarterly", {})
            for period_key, data in section.items():
                fiscal_date_str = data.get("date", period_key)
                try:
                    fiscal_date = date.fromisoformat(fiscal_date_str)
                except ValueError:
                    continue
                if fiscal_date < start or fiscal_date > end:
                    continue
                statements.append(
                    {
                        "fiscal_date": fiscal_date,
                        "statement_type": stmt_type,
                        "data": data,
                    }
                )
        return statements

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_statement(self, stmt: dict[str, Any]) -> None:
        """Validate basic accounting identities.

        Raises:
            DataQualityError: If validation fails.
        """
        data = stmt["data"]
        if stmt["statement_type"] == "balance_sheet":
            total_assets = Decimal(str(data.get("totalAssets", 0) or 0))
            total_liab = Decimal(str(data.get("totalLiab", 0) or 0))
            total_equity = Decimal(
                str(data.get("totalStockholderEquity", 0) or 0)
            )
            if total_assets > 0:
                diff = abs(total_assets - (total_liab + total_equity))
                tolerance = total_assets * Decimal("0.01")
                if diff > tolerance:
                    raise DataQualityError(
                        f"Balance sheet identity mismatch on "
                        f"{stmt['fiscal_date']}: assets={total_assets}, "
                        f"liab+equity={total_liab + total_equity}"
                    )

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_statements(
        self,
        symbol: str,
        statements: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert quarterly statements into ``equity_fundamentals``.

        Returns:
            Tuple of (inserted, updated) counts.
        """
        if not statements:
            return 0, 0

        inserted = 0
        updated = 0

        async with get_session() as session:
            for stmt in statements:
                result = await session.execute(
                    text("""
                        INSERT INTO equity_fundamentals
                            (symbol, fiscal_date, statement_type, data_json, updated_at)
                        VALUES
                            (:symbol, :fiscal_date, :statement_type,
                             :data_json::jsonb, NOW())
                        ON CONFLICT (symbol, fiscal_date, statement_type) DO UPDATE SET
                            data_json = EXCLUDED.data_json,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS is_insert
                    """),
                    {
                        "symbol": symbol,
                        "fiscal_date": stmt["fiscal_date"],
                        "statement_type": stmt["statement_type"],
                        "data_json": str(stmt["data"]),
                    },
                )
                is_insert = result.scalar()
                if is_insert:
                    inserted += 1
                else:
                    updated += 1

        return inserted, updated
