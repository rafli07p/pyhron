"""Kemenkeu APBN Realization and SBN Yields ingestion.

Source: Kementerian Keuangan (Ministry of Finance) data portals.

Data:
  - APBN (state budget) realization: revenue, expenditure, deficit
  - SBN (government bond) benchmark yields
  - Government debt statistics

Design:
  - Monthly APBN realization from data.kemenkeu.go.id
  - Daily SBN yields from DJPPR
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

KEMENKEU_API_BASE = "https://data.kemenkeu.go.id/api"
DJPPR_YIELD_URL = "https://www.djppr.kemenkeu.go.id/page/load-yield"
MAX_RETRIES = 3

APBN_INDICATORS: list[str] = [
    "apbn_tax_revenue",
    "apbn_non_tax_revenue",
    "apbn_total_revenue",
    "apbn_central_expenditure",
    "apbn_transfer_expenditure",
    "apbn_total_expenditure",
    "apbn_primary_balance",
    "apbn_fiscal_deficit",
    "apbn_deficit_to_gdp_pct",
]

SBN_TENORS: list[str] = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"]


@dataclass
class IngestionResult:
    """Outcome of an ingestion run."""

    source: str
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class KemenkeuAPBNRealizationIngester:
    """Ingester for Kemenkeu APBN realization and SBN yield data.

    Fetches monthly APBN budget realization figures and daily SBN
    benchmark yields from the Ministry of Finance data portals.

    Usage::

        ingester = KemenkeuAPBNRealizationIngester()
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
        """Ingest APBN realization and SBN yields over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="kemenkeu")

        all_records: list[dict[str, Any]] = []

        # Fetch APBN realization
        try:
            apbn = await self._fetch_apbn_realization(start, end)
            all_records.extend(apbn)
        except IngestionError as exc:
            result.errors.append(f"APBN fetch failed: {exc}")

        # Fetch SBN yields
        try:
            yields = await self._fetch_sbn_yields(start, end)
            all_records.extend(yields)
        except IngestionError as exc:
            result.errors.append(f"SBN yield fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="kemenkeu", symbol="FISCAL", operation="inserted").inc(inserted)

        self._logger.info(
            "kemenkeu_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_apbn_realization(
        self,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch monthly APBN realization data from Kemenkeu.

        Args:
            start: Start date.
            end: End date.

        Returns:
            Normalised APBN records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }
        params = {
            "start_period": start.isoformat(),
            "end_period": end.isoformat(),
            "format": "json",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(
                        f"{KEMENKEU_API_BASE}/apbn-realization",
                        params=params,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return self._parse_apbn_response(data, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"Kemenkeu APBN error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"Kemenkeu connection error: {exc}") from exc

        raise IngestionError(f"Kemenkeu APBN failed after {MAX_RETRIES} retries")

    async def _fetch_sbn_yields(
        self,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch daily SBN benchmark yields from DJPPR.

        Args:
            start: Start date.
            end: End date.

        Returns:
            Normalised SBN yield records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }
        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(DJPPR_YIELD_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    return self._parse_sbn_yields(data, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"DJPPR yield error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"DJPPR connection error: {exc}") from exc

        raise IngestionError(f"DJPPR yield fetch failed after {MAX_RETRIES} retries")

    # ── Parsing ──────────────────────────────────────────────────────────

    def _parse_apbn_response(
        self,
        data: dict[str, Any] | list[Any],
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse APBN realization response into normalised records.

        Args:
            data: Raw API response.
            start: Start date filter.
            end: End date filter.

        Returns:
            List of normalised APBN records.
        """
        records: list[dict[str, Any]] = []
        items = data.get("data", data) if isinstance(data, dict) else data

        for item in items:
            try:
                ref_date = date.fromisoformat(item.get("period", "")[:10])
            except (ValueError, TypeError):
                continue
            if ref_date < start or ref_date > end:
                continue

            for indicator in APBN_INDICATORS:
                field_name = indicator.replace("apbn_", "")
                value = item.get(field_name)
                if value is not None:
                    records.append(
                        {
                            "indicator": indicator,
                            "reference_date": ref_date,
                            "value": Decimal(str(value)),
                            "unit": "billion_idr",
                            "frequency": "monthly",
                        }
                    )

        return records

    def _parse_sbn_yields(
        self,
        data: dict[str, Any] | list[Any],
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse SBN yield curve data into normalised records.

        Args:
            data: Raw DJPPR response.
            start: Start date filter.
            end: End date filter.

        Returns:
            List of normalised SBN yield records.
        """
        records: list[dict[str, Any]] = []
        items = data.get("data", data) if isinstance(data, dict) else data

        for item in items:
            try:
                ref_date = date.fromisoformat(item.get("date", "")[:10])
            except (ValueError, TypeError):
                continue
            if ref_date < start or ref_date > end:
                continue

            for tenor in SBN_TENORS:
                yield_val = item.get(f"yield_{tenor}") or item.get(tenor)
                if yield_val is not None:
                    records.append(
                        {
                            "indicator": f"sbn_yield_{tenor.lower()}",
                            "reference_date": ref_date,
                            "value": Decimal(str(yield_val)),
                            "unit": "percent",
                            "frequency": "daily",
                        }
                    )

        return records

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a Kemenkeu record.

        Raises:
            DataQualityError: If validation fails.
        """
        if record["value"] is None:
            raise DataQualityError(f"Null value for {record['indicator']} on {record['reference_date']}")
        # SBN yields should be between 0% and 25%
        if record["indicator"].startswith("sbn_yield_"):
            v = float(record["value"])
            if v < 0 or v > 25:
                raise DataQualityError(f"SBN yield {v}% outside plausible range [0, 25] for {record['indicator']}")

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert records into ``macro_indicators``.

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
                            (:indicator, :reference_date, :value, :unit, :frequency,
                             'kemenkeu', NOW())
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
