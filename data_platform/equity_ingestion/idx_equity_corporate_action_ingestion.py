"""IDX Equity Corporate Action ingestion (dividends, stock splits).

Source: EODHD Dividends & Splits API.

Design:
  - Separate endpoints for dividends and splits
  - Idempotent upsert keyed on (symbol, action_type, ex_date)
  - Validates ex-date falls on a trading day
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


class IDXEquityCorporateActionIngester:
    """Corporate-action ingester for IDX equities (dividends & splits).

    Fetches dividend and split data from EODHD and upserts into the
    ``equity_corporate_actions`` table.

    Usage::

        ingester = IDXEquityCorporateActionIngester()
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
        """Ingest dividends and splits for *symbol* over [start, end].

        Args:
            symbol: IDX ticker (e.g. ``"BBCA"``).
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="eodhd")

        actions: list[dict[str, Any]] = []

        # Fetch dividends
        try:
            dividends = await self._fetch_dividends(symbol, start, end)
            actions.extend(dividends)
        except (IngestionError, RateLimitExceededError) as exc:
            result.errors.append(f"Dividend fetch failed: {exc}")

        # Fetch splits
        try:
            splits = await self._fetch_splits(symbol, start, end)
            actions.extend(splits)
        except (IngestionError, RateLimitExceededError) as exc:
            result.errors.append(f"Split fetch failed: {exc}")

        valid: list[dict[str, Any]] = []
        for action in actions:
            try:
                self._validate_action(action)
                valid.append(action)
            except DataQualityError as exc:
                result.errors.append(str(exc))
                result.rows_skipped += 1

        inserted, updated = await self._upsert_actions(symbol, valid)
        result.rows_inserted = inserted
        result.rows_updated = updated
        result.duration_ms = (time.monotonic() - t0) * 1000

        INGESTION_ROWS.labels(
            source="eodhd", symbol=symbol, operation="inserted"
        ).inc(inserted)

        self._logger.info(
            "corporate_action_ingestion_complete",
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
        """Ingest corporate actions for multiple symbols.

        Args:
            symbols: List of IDX tickers.
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            One ``IngestionResult`` per symbol.
        """
        results: list[IngestionResult] = []
        for sym in symbols:
            results.append(await self.ingest_for_date_range(sym, start, end))
        return results

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_dividends(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch dividend history from EODHD.

        Returns:
            Normalised list of dividend action dicts.
        """
        data = await self._eodhd_request(
            f"https://eodhd.com/api/div/{symbol}.IDX",
            start_date,
            end_date,
        )
        return [
            {
                "action_type": "dividend",
                "ex_date": date.fromisoformat(row["date"]),
                "value": Decimal(str(row["value"])),
                "currency": row.get("currency", "IDR"),
            }
            for row in data
        ]

    async def _fetch_splits(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch stock-split history from EODHD.

        Returns:
            Normalised list of split action dicts.
        """
        data = await self._eodhd_request(
            f"https://eodhd.com/api/splits/{symbol}.IDX",
            start_date,
            end_date,
        )
        return [
            {
                "action_type": "split",
                "ex_date": date.fromisoformat(row["date"]),
                "value": Decimal(str(row["split"])) if "/" not in str(row["split"]) else self._parse_split_ratio(str(row["split"])),
                "currency": "IDR",
            }
            for row in data
        ]

    async def _eodhd_request(
        self,
        url: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Make a rate-limited request to EODHD.

        Raises:
            IngestionError: On API failure.
            RateLimitExceededError: When daily limit is exceeded.
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

        params = {
            "api_token": self._eodhd_key,
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "fmt": "json",
        }

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
                raise IngestionError(f"EODHD error: {exc}") from exc
            except httpx.RequestError as exc:
                raise IngestionError(f"EODHD connection error: {exc}") from exc

        raise IngestionError(f"EODHD failed after {MAX_RETRIES} retries")

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_split_ratio(ratio_str: str) -> Decimal:
        """Parse a split ratio string like ``'2/1'`` into a Decimal.

        Args:
            ratio_str: Split ratio in ``"numerator/denominator"`` format.

        Returns:
            Decimal representation of the ratio.
        """
        parts = ratio_str.split("/")
        if len(parts) == 2:
            return Decimal(parts[0]) / Decimal(parts[1])
        return Decimal(ratio_str)

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_action(self, action: dict[str, Any]) -> None:
        """Validate a corporate action record.

        Raises:
            DataQualityError: If validation fails.
        """
        if action["value"] <= 0:
            raise DataQualityError(
                f"Non-positive value {action['value']} for "
                f"{action['action_type']} on {action['ex_date']}"
            )
        # ex-date must not be a weekend
        if action["ex_date"].weekday() >= 5:
            raise DataQualityError(
                f"Ex-date {action['ex_date']} falls on a weekend for "
                f"{action['action_type']}"
            )

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_actions(
        self,
        symbol: str,
        actions: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert corporate actions into ``equity_corporate_actions``.

        Returns:
            Tuple of (inserted, updated) counts.
        """
        if not actions:
            return 0, 0

        inserted = 0
        updated = 0

        async with get_session() as session:
            for action in actions:
                result = await session.execute(
                    text("""
                        INSERT INTO equity_corporate_actions
                            (symbol, action_type, ex_date, value, currency, updated_at)
                        VALUES
                            (:symbol, :action_type, :ex_date, :value, :currency, NOW())
                        ON CONFLICT (symbol, action_type, ex_date) DO UPDATE SET
                            value = EXCLUDED.value,
                            currency = EXCLUDED.currency,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS is_insert
                    """),
                    {
                        "symbol": symbol,
                        "action_type": action["action_type"],
                        "ex_date": action["ex_date"],
                        "value": float(action["value"]),
                        "currency": action["currency"],
                    },
                )
                is_insert = result.scalar()
                if is_insert:
                    inserted += 1
                else:
                    updated += 1

        return inserted, updated
