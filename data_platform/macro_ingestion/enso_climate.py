"""ENSO Climate Index (El Nino / La Nina) ingestion.

Source: NOAA Climate Prediction Center
  - Oceanic Nino Index (ONI): https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
  - SOI (Southern Oscillation Index)

Design:
  - Monthly ONI values (3-month running mean of SST anomalies in Nino 3.4)
  - Classification: El Nino (ONI >= +0.5), La Nina (ONI <= -0.5), Neutral
  - Critical for Indonesian agriculture (CPO, rice) and coal demand forecasting
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

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
SOI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/soi"
MAX_RETRIES = 3

# 3-month season labels used in NOAA ONI data
SEASON_TO_MONTH: dict[str, int] = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
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


class ENSOClimateIndexIngester:
    """Ingester for ENSO climate indices from NOAA.

    Fetches the Oceanic Nino Index (ONI) and optionally the SOI from
    NOAA's Climate Prediction Center. These indices are critical for
    agricultural commodity yield forecasting in Indonesia.

    Usage::

        ingester = ENSOClimateIndexIngester()
        result = await ingester.ingest_for_date_range(
            start=date(2020, 1, 1),
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
        """Ingest ENSO indices over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="noaa")

        all_records: list[dict[str, Any]] = []

        # Fetch ONI
        try:
            oni_records = await self._fetch_oni(start, end)
            all_records.extend(oni_records)
        except IngestionError as exc:
            result.errors.append(f"ONI fetch failed: {exc}")

        # Fetch SOI
        try:
            soi_records = await self._fetch_soi(start, end)
            all_records.extend(soi_records)
        except IngestionError as exc:
            result.errors.append(f"SOI fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="noaa", symbol="ENSO", operation="inserted").inc(inserted)

        self._logger.info(
            "enso_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # Data fetch

    async def _fetch_oni(
        self,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch ONI (Oceanic Nino Index) from NOAA.

        The ONI data is published as a plain-text ASCII file with columns:
        YEAR  SEASON  TOTAL  ANOM

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised ONI records.

        Raises:
            IngestionError: On fetch failure.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(ONI_URL)
                    resp.raise_for_status()
                    return self._parse_oni_text(resp.text, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"NOAA ONI error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"NOAA connection error: {exc}") from exc

        raise IngestionError(f"NOAA ONI failed after {MAX_RETRIES} retries")

    async def _fetch_soi(
        self,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch SOI (Southern Oscillation Index) from NOAA.

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised SOI records.

        Raises:
            IngestionError: On fetch failure.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(SOI_URL)
                    resp.raise_for_status()
                    return self._parse_soi_text(resp.text, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"NOAA SOI error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"NOAA SOI connection error: {exc}") from exc

        raise IngestionError(f"NOAA SOI failed after {MAX_RETRIES} retries")

    # Parsing

    def _parse_oni_text(
        self,
        text_data: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse NOAA ONI ASCII data.

        Args:
            text_data: Raw text from ONI file.
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised ONI records with ENSO classification.
        """
        records: list[dict[str, Any]] = []

        for line in text_data.strip().splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue

            try:
                year = int(parts[0])
                season = parts[1].upper()
                anom = Decimal(parts[3])
            except (ValueError, IndexError):
                continue

            month = SEASON_TO_MONTH.get(season)
            if month is None:
                continue

            try:
                ref_date = date(year, month, 1)
            except ValueError:
                continue

            if ref_date < start or ref_date > end:
                continue

            # Classify ENSO phase
            anom_float = float(anom)
            if anom_float >= 0.5:
                phase = "el_nino"
            elif anom_float <= -0.5:
                phase = "la_nina"
            else:
                phase = "neutral"

            records.append(
                {
                    "indicator": "oni_enso_index",
                    "reference_date": ref_date,
                    "value": anom,
                    "unit": "degrees_c_anomaly",
                    "frequency": "monthly",
                    "metadata": {"season": season, "phase": phase},
                }
            )

        return records

    def _parse_soi_text(
        self,
        text_data: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse NOAA SOI text data.

        Args:
            text_data: Raw text from SOI file.
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised SOI records.
        """
        records: list[dict[str, Any]] = []

        for line in text_data.strip().splitlines():
            parts = line.split()
            if len(parts) < 13:
                continue

            try:
                year = int(parts[0])
            except ValueError:
                continue

            for month_idx in range(1, 13):
                try:
                    value = Decimal(parts[month_idx])
                except (ValueError, IndexError):
                    continue

                # NOAA uses -999.9 for missing
                if value < Decimal("-900"):
                    continue

                try:
                    ref_date = date(year, month_idx, 1)
                except ValueError:
                    continue

                if ref_date < start or ref_date > end:
                    continue

                records.append(
                    {
                        "indicator": "soi_index",
                        "reference_date": ref_date,
                        "value": value,
                        "unit": "index",
                        "frequency": "monthly",
                        "metadata": {},
                    }
                )

        return records

    # Validation

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate an ENSO index record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if record["indicator"] == "oni_enso_index":
            # ONI historically ranges from about -2.5 to +2.5
            if v < -4.0 or v > 4.0:
                raise DataQualityError(
                    f"ONI value {v} outside plausible range [-4.0, 4.0] on {record['reference_date']}"
                )
        if record["indicator"] == "soi_index" and (v < -50 or v > 50):
            raise DataQualityError(f"SOI value {v} outside plausible range [-50, 50] on {record['reference_date']}")

    # Persistence

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert ENSO records into ``macro_indicators``.

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
                        INSERT INTO macro_indicators
                            (indicator, reference_date, value, unit, frequency, source, updated_at)
                        VALUES
                            (:indicator, :reference_date, :value, :unit, :frequency, 'noaa', NOW())
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
