"""CPO (Crude Palm Oil) price ingestion from MPOB Malaysia.

Source: Malaysian Palm Oil Board (``mpob.gov.my``)

Design:
  - Monthly CPO prices (FOB Malaysia) -- benchmark for global palm oil
  - Daily settlement from Bursa Malaysia Derivatives (BMD)
  - Used for IDX plantation sector valuation (AALI, LSIP, SSMS, DSNG)
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

MPOB_API_URL = "https://bepi.mpob.gov.my/api/v1/prices"
BMD_CPO_URL = "https://www.bursamalaysia.com/market_information/derivatives"
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


class CPOPriceMPOBIngester:
    """CPO price ingester from MPOB Malaysia.

    Fetches CPO FOB Malaysia prices and BMD futures settlement prices
    to provide a comprehensive palm oil price dataset.

    Usage::

        ingester = CPOPriceMPOBIngester()
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
    ) -> IngestionResult:
        """Ingest CPO prices over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="mpob")

        all_records: list[dict[str, Any]] = []

        # Monthly MPOB prices
        try:
            monthly = await self._fetch_mpob_monthly(start, end)
            all_records.extend(monthly)
        except IngestionError as exc:
            result.errors.append(f"MPOB monthly fetch failed: {exc}")

        # Daily BMD settlement
        try:
            daily = await self._fetch_bmd_settlement(start, end)
            all_records.extend(daily)
        except IngestionError as exc:
            result.errors.append(f"BMD settlement fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="mpob", symbol="CPO", operation="inserted").inc(inserted)

        self._logger.info(
            "cpo_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # Data fetch

    async def _fetch_mpob_monthly(
        self,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch monthly CPO FOB prices from MPOB.

        Args:
            start: Start date.
            end: End date.

        Returns:
            Normalised CPO monthly records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }
        params = {
            "product": "cpo",
            "start": start.isoformat(),
            "end": end.isoformat(),
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(MPOB_API_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    return self._parse_mpob_response(data, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"MPOB API error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"MPOB connection error: {exc}") from exc

        raise IngestionError(f"MPOB fetch failed after {MAX_RETRIES} retries")

    async def _fetch_bmd_settlement(
        self,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch daily BMD CPO futures settlement prices.

        Args:
            start: Start date.
            end: End date.

        Returns:
            Normalised BMD settlement records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(BMD_CPO_URL, headers=headers)
                    resp.raise_for_status()
                    return self._parse_bmd_response(resp.text, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BMD API error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BMD connection error: {exc}") from exc

        raise IngestionError(f"BMD fetch failed after {MAX_RETRIES} retries")

    # Parsing

    def _parse_mpob_response(
        self,
        data: dict[str, Any] | list[Any],
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse MPOB API response into normalised records.

        Args:
            data: Raw API response.
            start: Start date filter.
            end: End date filter.

        Returns:
            List of normalised CPO records.
        """
        records: list[dict[str, Any]] = []
        items = data.get("data", data) if isinstance(data, dict) else data

        for item in items:
            try:
                ref_date = date.fromisoformat(item.get("date", item.get("period", ""))[:10])
            except (ValueError, TypeError):
                continue
            if ref_date < start or ref_date > end:
                continue

            price = item.get("price") or item.get("cpo_price") or item.get("value")
            if price is None:
                continue

            records.append(
                {
                    "indicator": "cpo_fob_malaysia",
                    "reference_date": ref_date,
                    "value": Decimal(str(price)),
                    "unit": "myr_per_ton",
                    "frequency": "monthly",
                }
            )

        return records

    def _parse_bmd_response(
        self,
        html_or_json: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse BMD settlement data.

        Args:
            html_or_json: Raw response content.
            start: Start date filter.
            end: End date filter.

        Returns:
            List of normalised BMD settlement records.
        """
        # Placeholder for actual BMD parsing logic
        self._logger.info("bmd_parsing", content_length=len(html_or_json))
        return []

    # Validation

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a CPO price record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if v <= 0:
            raise DataQualityError(f"Non-positive CPO price {v} on {record['reference_date']}")
        # CPO historically ranges from ~1000 to ~7000 MYR/ton
        if record["unit"] == "myr_per_ton" and (v < 500 or v > 10000):
            raise DataQualityError(f"CPO price {v} MYR/ton outside plausible range [500, 10000]")

    # Persistence

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert CPO records into ``commodity_prices``.

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
                            (:indicator, :reference_date, :value, :unit, :frequency, 'mpob', NOW())
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
