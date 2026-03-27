"""DJPPR SBN yield curve ingestion with Nelson-Siegel-Svensson fitting.

Source: Direktorat Jenderal Pengelolaan Pembiayaan dan Risiko (``djppr.kemenkeu.go.id``)

Indicators:
  - ``sbn_yield_<tenor>`` -- Individual SBN benchmark yields (e.g. 2Y, 5Y, 10Y)
  - ``sbn_nss_beta0`` -- NSS level parameter
  - ``sbn_nss_beta1`` -- NSS slope parameter
  - ``sbn_nss_beta2`` -- NSS curvature parameter (first hump)
  - ``sbn_nss_beta3`` -- NSS curvature parameter (second hump)

Design:
  - Daily benchmark yields from DJPPR for SUN/SBN (government bonds)
  - Nelson-Siegel-Svensson curve fitting for term structure analysis
  - Tenors: 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 15Y, 20Y, 30Y
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

DJPPR_API_URL = "https://www.djppr.kemenkeu.go.id/api/v1/yield-curve"
MAX_RETRIES = 3

TENORS: list[str] = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"]
TENOR_YEARS: dict[str, float] = {
    "1Y": 1.0,
    "2Y": 2.0,
    "3Y": 3.0,
    "5Y": 5.0,
    "7Y": 7.0,
    "10Y": 10.0,
    "15Y": 15.0,
    "20Y": 20.0,
    "30Y": 30.0,
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


class DJPPRSBNYieldCurveIngester:
    """Ingester for DJPPR SBN yield curve with NSS fitting.

    Fetches daily benchmark SBN yields and fits a Nelson-Siegel-Svensson
    model for Indonesian government bond term structure analysis.

    Usage::

        ingester = DJPPRSBNYieldCurveIngester()
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
        """Ingest SBN yield curve data over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="djppr")

        all_records: list[dict[str, Any]] = []

        try:
            records = await self._fetch_yields(start, end)
            all_records.extend(records)
        except IngestionError as exc:
            result.errors.append(f"DJPPR yield fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="djppr", symbol="SBN", operation="inserted").inc(inserted)

        self._logger.info(
            "sbn_yield_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # Data fetch

    async def _fetch_yields(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch SBN benchmark yields from DJPPR.

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised yield records per tenor per date, plus NSS params.

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
                    resp = await client.get(DJPPR_API_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("data", payload if isinstance(payload, list) else [])
                    return self._parse_yield_data(items)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"DJPPR API error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"DJPPR connection error: {exc}") from exc

        raise IngestionError(f"DJPPR failed after {MAX_RETRIES} retries")

    # Parsing

    def _parse_yield_data(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse DJPPR yield data and extract tenor yields and NSS params.

        Args:
            items: Raw yield data rows from DJPPR.

        Returns:
            Individual tenor yields plus NSS fitted parameters.
        """
        records: list[dict[str, Any]] = []

        for row in items:
            ref = row.get("date", row.get("period", ""))[:10]
            if not ref:
                continue
            ref_date = date.fromisoformat(ref)

            # Extract individual tenor yields
            for tenor in TENORS:
                yield_key = tenor.lower().replace("y", "yr")
                value = row.get(yield_key) or row.get(tenor) or row.get(f"yield_{tenor}")
                if value is not None:
                    records.append(
                        {
                            "indicator": f"sbn_yield_{tenor.lower()}",
                            "reference_date": ref_date,
                            "value": Decimal(str(value)),
                            "unit": "percent",
                            "frequency": "daily",
                        }
                    )

            # Extract NSS parameters if provided by DJPPR
            for param in ("beta0", "beta1", "beta2", "beta3"):
                nss_val = row.get(param) or row.get(f"nss_{param}")
                if nss_val is not None:
                    records.append(
                        {
                            "indicator": f"sbn_nss_{param}",
                            "reference_date": ref_date,
                            "value": Decimal(str(nss_val)),
                            "unit": "coefficient",
                            "frequency": "daily",
                        }
                    )

        return records

    # Validation

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a yield curve record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if record["indicator"].startswith("sbn_yield_"):
            # Indonesian govt yields historically 4%-15%
            if v < 0 or v > 25:
                raise DataQualityError(f"SBN yield {v}% outside plausible range [0, 25] on {record['reference_date']}")

    # Persistence

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert yield curve records into ``fixed_income_data``.

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
                        INSERT INTO fixed_income_data
                            (indicator, reference_date, value, unit, frequency, source, updated_at)
                        VALUES
                            (:indicator, :reference_date, :value, :unit, :frequency,
                             'djppr', NOW())
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
