"""NASA FIRMS VIIRS 375m fire hotspot data ingestion.

Source: NASA Fire Information for Resource Management System (FIRMS)
  - VIIRS 375m active fire product (``firms.modaps.eosdis.nasa.gov``)

Indicators:
  - ``viirs_hotspot_count`` -- Daily fire hotspot count by province
  - ``viirs_frp_total`` -- Daily total fire radiative power (MW)

Design:
  - Fetches VIIRS I-Band 375m active fire data for Indonesia (country=IDN)
  - Aggregated by province for plantation and forestry fire monitoring
  - Critical leading indicator for CPO supply disruption and haze events
  - Idempotent upsert keyed on (indicator, reference_date, province)
"""

from __future__ import annotations

import asyncio
import csv
import io
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

FIRMS_API_URL = "https://firms.modaps.eosdis.nasa.gov/api/country/csv"
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


class NASAFIRMSFireHotspotIngester:
    """Ingester for NASA FIRMS VIIRS 375m fire hotspot data.

    Fetches active fire detections over Indonesia from NASA FIRMS
    and aggregates by province and date for plantation fire monitoring.

    Usage::

        ingester = NASAFIRMSFireHotspotIngester()
        result = await ingester.ingest_recent(days=10)
    """

    def __init__(self) -> None:
        self._config = get_config()
        self._logger = get_logger(__name__)

    # ── Public API ───────────────────────────────────────────────────────

    async def ingest_recent(
        self,
        days: int = 10,
    ) -> IngestionResult:
        """Ingest recent VIIRS fire hotspot data.

        Args:
            days: Number of recent days to fetch (max 10 for FIRMS API).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="nasa_firms")

        all_records: list[dict[str, Any]] = []

        try:
            records = await self._fetch_viirs(days)
            all_records.extend(records)
        except IngestionError as exc:
            result.errors.append(f"VIIRS fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="nasa_firms", symbol="FIRE", operation="inserted").inc(inserted)

        self._logger.info(
            "firms_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_viirs(self, days: int) -> list[dict[str, Any]]:
        """Fetch VIIRS active fire data from NASA FIRMS.

        Args:
            days: Number of recent days to fetch.

        Returns:
            Province-aggregated fire hotspot records.

        Raises:
            IngestionError: On fetch failure.
        """
        api_key = self._config.nasa_firms_api_key
        url = f"{FIRMS_API_URL}/{api_key}/VIIRS_SNPP_NRT/IDN/{days}"
        headers = {"User-Agent": "Pyhron/1.0 (Data Platform)"}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    return self._parse_csv(resp.text)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"FIRMS API error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"FIRMS connection error: {exc}") from exc

        raise IngestionError(f"FIRMS failed after {MAX_RETRIES} retries")

    # ── Parsing ──────────────────────────────────────────────────────────

    def _parse_csv(self, csv_text: str) -> list[dict[str, Any]]:
        """Parse FIRMS CSV and aggregate by province and date.

        Args:
            csv_text: Raw CSV text from FIRMS.

        Returns:
            Aggregated hotspot count and FRP records per province per day.
        """
        reader = csv.DictReader(io.StringIO(csv_text))
        aggregation: dict[tuple[str, str], dict[str, Any]] = {}

        for row in reader:
            acq_date = row.get("acq_date", "")
            province = row.get("admin1", "unknown")
            frp = float(row.get("frp", 0))

            key = (acq_date, province)
            if key not in aggregation:
                aggregation[key] = {"count": 0, "frp_total": 0.0}
            aggregation[key]["count"] += 1
            aggregation[key]["frp_total"] += frp

        records: list[dict[str, Any]] = []
        for (acq_date, province), agg in aggregation.items():
            try:
                ref_date = date.fromisoformat(acq_date)
            except ValueError:
                continue

            records.append(
                {
                    "indicator": "viirs_hotspot_count",
                    "reference_date": ref_date,
                    "value": Decimal(str(agg["count"])),
                    "unit": "count",
                    "frequency": "daily",
                    "province": province,
                }
            )
            records.append(
                {
                    "indicator": "viirs_frp_total",
                    "reference_date": ref_date,
                    "value": Decimal(str(round(agg["frp_total"], 2))),
                    "unit": "megawatts",
                    "frequency": "daily",
                    "province": province,
                }
            )

        return records

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a fire hotspot record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if v < 0:
            raise DataQualityError(f"Negative value {v} for {record['indicator']} on {record['reference_date']}")

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert fire hotspot records into ``alternative_data``.

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
                        INSERT INTO alternative_data
                            (indicator, reference_date, value, unit, frequency,
                             province, source, updated_at)
                        VALUES
                            (:indicator, :reference_date, :value, :unit, :frequency,
                             :province, 'nasa_firms', NOW())
                        ON CONFLICT (indicator, reference_date, province) DO UPDATE SET
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
                        "province": rec.get("province", ""),
                    },
                )
                is_insert = result.scalar()
                if is_insert:
                    inserted += 1
                else:
                    updated += 1

        return inserted, updated
