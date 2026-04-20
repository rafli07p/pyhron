"""BKPM FDI / investment realization quarterly data ingestion.

Source: Badan Koordinasi Penanaman Modal (``bkpm.go.id``)

Indicators:
  - ``fdi_realization_usd`` -- Quarterly FDI realization (USD millions)
  - ``ddi_realization_idr`` -- Quarterly DDI realization (IDR billions)
  - ``fdi_projects_count`` -- Number of FDI projects approved

Design:
  - Quarterly data from BKPM press releases / API
  - Key macro indicator for capital flows and IDR demand
  - Breakdown by sector available in metadata
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

BKPM_API_URL = "https://nswi.bkpm.go.id/api/v1/realization"
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


class BKPMInvestmentRealizationIngester:
    """Ingester for BKPM quarterly FDI / DDI realization data.

    Fetches investment realization figures from BKPM for tracking
    foreign and domestic direct investment flows into Indonesia.

    Usage::

        ingester = BKPMInvestmentRealizationIngester()
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
        """Ingest BKPM investment data over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="bkpm")

        all_records: list[dict[str, Any]] = []

        try:
            records = await self._fetch_realization(start, end)
            all_records.extend(records)
        except IngestionError as exc:
            result.errors.append(f"BKPM fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="bkpm", symbol="FDI", operation="inserted").inc(inserted)

        self._logger.info(
            "bkpm_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # Data fetch

    async def _fetch_realization(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch quarterly investment realization from BKPM.

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised FDI and DDI records.

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
                    resp = await client.get(BKPM_API_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("data", payload if isinstance(payload, list) else [])
                    records: list[dict[str, Any]] = []
                    for row in items:
                        ref = row.get("date", row.get("period", ""))[:10]
                        if not ref:
                            continue
                        ref_date = date.fromisoformat(ref)
                        if row.get("fdi_usd"):
                            records.append(
                                {
                                    "indicator": "fdi_realization_usd",
                                    "reference_date": ref_date,
                                    "value": Decimal(str(row["fdi_usd"])),
                                    "unit": "million_usd",
                                    "frequency": "quarterly",
                                }
                            )
                        if row.get("ddi_idr"):
                            records.append(
                                {
                                    "indicator": "ddi_realization_idr",
                                    "reference_date": ref_date,
                                    "value": Decimal(str(row["ddi_idr"])),
                                    "unit": "billion_idr",
                                    "frequency": "quarterly",
                                }
                            )
                        if row.get("projects"):
                            records.append(
                                {
                                    "indicator": "fdi_projects_count",
                                    "reference_date": ref_date,
                                    "value": Decimal(str(row["projects"])),
                                    "unit": "count",
                                    "frequency": "quarterly",
                                }
                            )
                    return records
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BKPM API error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BKPM connection error: {exc}") from exc

        raise IngestionError(f"BKPM failed after {MAX_RETRIES} retries")

    # Validation

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate an investment realization record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if v < 0:
            raise DataQualityError(
                f"Negative investment value {v} for {record['indicator']} on {record['reference_date']}"
            )

    # Persistence

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert investment records into ``alternative_data``.

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
                            (indicator, reference_date, value, unit, frequency, source, updated_at)
                        VALUES
                            (:indicator, :reference_date, :value, :unit, :frequency,
                             'bkpm', NOW())
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
