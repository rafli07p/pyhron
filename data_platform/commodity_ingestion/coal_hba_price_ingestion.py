"""HBA (Harga Batubara Acuan) coal reference price ingestion.

Source:
  - Indonesian ESDM (Kementerian ESDM) monthly HBA decree
  - Newcastle coal futures (globalCOAL API / ICE)

Indicators:
  - ``hba_coal_price`` -- Monthly HBA reference price (USD/ton, GAR 6322)
  - ``newcastle_coal_price`` -- Daily Newcastle coal futures settlement

Design:
  - HBA is the government-set monthly benchmark for Indonesian coal royalties
  - Newcastle provides the daily international reference
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

from shared.configuration_settings import get_config
from shared.async_database_session import get_session
from shared.platform_exception_hierarchy import (
    DataQualityError,
    IngestionError,
)
from shared.structured_json_logger import get_logger
from shared.prometheus_metrics_registry import INGESTION_ROWS

logger = get_logger(__name__)

ESDM_HBA_URL = "https://www.minerba.esdm.go.id/api/hba"
NEWCASTLE_API_URL = "https://api.globalcoal.com/v1/newcastle"
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


class CoalHBAPriceIngester:
    """Ingester for Indonesian HBA coal reference and Newcastle prices.

    Fetches the monthly HBA decree price from ESDM and daily Newcastle
    coal futures for comprehensive coal market coverage.

    Usage::

        ingester = CoalHBAPriceIngester()
        result = await ingester.ingest_for_date_range(
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )
    """

    def __init__(self) -> None:
        self._config = get_config()
        self._logger = get_logger(__name__)

    # ── Public API ───────────────────────────────────────────────────────

    async def ingest_for_date_range(
        self,
        start: date,
        end: date,
    ) -> IngestionResult:
        """Ingest HBA and Newcastle coal prices over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="esdm")

        all_records: list[dict[str, Any]] = []

        # Monthly HBA from ESDM
        try:
            hba = await self._fetch_hba(start, end)
            all_records.extend(hba)
        except IngestionError as exc:
            result.errors.append(f"HBA fetch failed: {exc}")

        # Daily Newcastle coal
        try:
            newcastle = await self._fetch_newcastle(start, end)
            all_records.extend(newcastle)
        except IngestionError as exc:
            result.errors.append(f"Newcastle fetch failed: {exc}")

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

        INGESTION_ROWS.labels(
            source="esdm", symbol="COAL", operation="inserted"
        ).inc(inserted)

        self._logger.info(
            "coal_hba_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_hba(
        self, start: date, end: date
    ) -> list[dict[str, Any]]:
        """Fetch monthly HBA prices from ESDM.

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised HBA records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }
        params = {"start": start.isoformat(), "end": end.isoformat()}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(
                        ESDM_HBA_URL, params=params, headers=headers
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("data", payload if isinstance(payload, list) else [])
                    return [
                        {
                            "indicator": "hba_coal_price",
                            "reference_date": date.fromisoformat(row.get("date", row.get("period", ""))[:10]),
                            "value": Decimal(str(row.get("price", row.get("value", 0)))),
                            "unit": "usd_per_ton",
                            "frequency": "monthly",
                        }
                        for row in items
                        if row.get("date") or row.get("period")
                    ]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ESDM HBA error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ESDM connection error: {exc}") from exc

        raise IngestionError(f"ESDM HBA failed after {MAX_RETRIES} retries")

    async def _fetch_newcastle(
        self, start: date, end: date
    ) -> list[dict[str, Any]]:
        """Fetch daily Newcastle coal futures prices.

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised Newcastle coal records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
            "Authorization": f"Bearer {self._config.get('GLOBALCOAL_API_KEY', '')}",
        }
        params = {"from": start.isoformat(), "to": end.isoformat()}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(
                        NEWCASTLE_API_URL, params=params, headers=headers
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("data", payload if isinstance(payload, list) else [])
                    return [
                        {
                            "indicator": "newcastle_coal_price",
                            "reference_date": date.fromisoformat(row["date"][:10]),
                            "value": Decimal(str(row.get("settlement", row.get("close", 0)))),
                            "unit": "usd_per_ton",
                            "frequency": "daily",
                        }
                        for row in items
                        if row.get("date")
                    ]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"Newcastle API error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"Newcastle connection error: {exc}") from exc

        raise IngestionError(f"Newcastle failed after {MAX_RETRIES} retries")

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a coal price record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if v <= 0:
            raise DataQualityError(
                f"Non-positive coal price {v} on {record['reference_date']}"
            )
        # HBA historically ranges from ~50 to ~350 USD/ton
        if v < 20 or v > 500:
            raise DataQualityError(
                f"Coal price {v} USD/ton outside plausible range [20, 500]"
            )

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert coal price records into ``commodity_prices``.

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
                            (:indicator, :reference_date, :value, :unit, :frequency, 'esdm', NOW())
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
