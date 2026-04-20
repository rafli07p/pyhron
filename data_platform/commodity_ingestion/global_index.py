"""Bloomberg Commodity Index ingestion via EODHD API.

Source: EODHD Historical Data API (``eodhistoricaldata.com``)

Indicators:
  - ``bcom_index`` -- Bloomberg Commodity Index (total return)
  - ``bcom_energy`` -- BCOM Energy sub-index
  - ``bcom_metals`` -- BCOM Industrial Metals sub-index
  - ``bcom_agriculture`` -- BCOM Agriculture sub-index

Design:
  - Daily index values via EODHD EOD endpoint
  - Provides macro commodity cycle context for Indonesian exposure
  - Idempotent upsert keyed on (indicator, reference_date)
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
)
from shared.prometheus_metrics_registry import INGESTION_ROWS
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

EODHD_BASE_URL = "https://eodhistoricaldata.com/api/eod"
MAX_RETRIES = 3

# EODHD ticker symbols for BCOM indices
BCOM_TICKERS: dict[str, str] = {
    "bcom_index": "BCOM.INDX",
    "bcom_energy": "BCOMEN.INDX",
    "bcom_metals": "BCOMIN.INDX",
    "bcom_agriculture": "BCOMAG.INDX",
}


@dataclass
class IngestionResult:
    """Outcome of an ingestion run."""

    source: str
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class GlobalCommodityIndexIngester:
    """Ingester for Bloomberg Commodity Index via EODHD API.

    Fetches BCOM total return and sub-index values to provide
    commodity cycle context for Indonesian market analysis.

    Usage::

        ingester = GlobalCommodityIndexIngester()
        result = await ingester.ingest_for_date_range(
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )
    """

    def __init__(self) -> None:
        self._config = get_config()
        self._logger = get_logger(__name__)

    # Public API

    async def ingest_for_date_range(
        self,
        start: date,
        end: date,
        indicators: list[str] | None = None,
    ) -> IngestionResult:
        """Ingest BCOM index values over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).
            indicators: Subset of BCOM indicators; defaults to all.

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="eodhd")
        target = indicators or list(BCOM_TICKERS.keys())

        all_records: list[dict[str, Any]] = []
        for indicator in target:
            try:
                records = await self._fetch_index(indicator, start, end)
                all_records.extend(records)
            except IngestionError as exc:
                result.errors.append(f"{indicator}: {exc}")

        valid: list[dict[str, Any]] = []
        for rec in all_records:
            try:
                self._validate_record(rec)
                valid.append(rec)
            except DataQualityError as exc:
                result.errors.append(str(exc))
                result.rows_skipped += 1

        inserted, updated = await self._upsert_records(valid)
        result.rows_inserted = inserted
        result.rows_updated = updated
        result.duration_ms = (time.monotonic() - t0) * 1000

        INGESTION_ROWS.labels(source="eodhd", symbol="BCOM", operation="inserted").inc(inserted)

        self._logger.info(
            "bcom_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # Data fetch

    async def _fetch_index(self, indicator: str, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch a single BCOM index from EODHD.

        Args:
            indicator: BCOM indicator code.
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised index records.

        Raises:
            IngestionError: On fetch failure.
        """
        ticker = BCOM_TICKERS.get(indicator)
        if ticker is None:
            raise IngestionError(f"Unknown indicator: {indicator}")

        api_key = self._config.eodhd_api_key
        url = f"{EODHD_BASE_URL}/{ticker}"
        headers = {"User-Agent": "Pyhron/1.0 (Data Platform)"}
        params = {
            "api_token": api_key,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "fmt": "json",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    return [
                        {
                            "indicator": indicator,
                            "reference_date": date.fromisoformat(row["date"][:10]),
                            "value": Decimal(str(row.get("close", row.get("adjusted_close", 0)))),
                            "unit": "index",
                            "frequency": "daily",
                        }
                        for row in data
                        if row.get("date")
                    ]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"EODHD error ({ticker}): {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"EODHD connection error ({ticker}): {exc}") from exc

        raise IngestionError(f"EODHD {ticker} failed after {MAX_RETRIES} retries")

    # Validation

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a BCOM index record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if v <= 0:
            raise DataQualityError(f"Non-positive index value {v} on {record['reference_date']}")

    # Persistence

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert BCOM records into ``commodity_prices``.

        Returns:
            Tuple of (inserted, updated) counts.
        """
        if not records:
            return 0, 0

        inserted = 0
        updated = 0

        async with get_session() as session:
            for rec in records:
                result = await session.execute(
                    text("""
                        INSERT INTO commodity_prices
                            (indicator, reference_date, value, unit, frequency, source, updated_at)
                        VALUES
                            (:indicator, :reference_date, :value, :unit, :frequency, 'eodhd', NOW())
                        ON CONFLICT (indicator, reference_date) DO UPDATE SET
                            value = EXCLUDED.value,
                            unit = EXCLUDED.unit,
                            source = EXCLUDED.source,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS is_insert
                    """),
                    {
                        "indicator": rec["indicator"],
                        "reference_date": rec["reference_date"],
                        "value": float(rec["value"]),
                        "unit": rec["unit"],
                        "frequency": rec["frequency"],
                    },
                )
                is_insert = result.scalar()
                if is_insert:
                    inserted += 1
                else:
                    updated += 1

        return inserted, updated
