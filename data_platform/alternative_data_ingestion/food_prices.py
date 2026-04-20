"""Panel Harga Pangan (staple food prices) ingestion.

Source: Pusat Informasi Harga Pangan Strategis Nasional
  - ``panelharga.badanpangan.go.id``

Indicators:
  - ``harga_beras_medium`` -- Medium quality rice price (IDR/kg)
  - ``harga_gula_pasir`` -- Granulated sugar price (IDR/kg)
  - ``harga_minyak_goreng`` -- Cooking oil price (IDR/liter)
  - ``harga_daging_sapi`` -- Beef price (IDR/kg)
  - ``harga_cabai_merah`` -- Red chili price (IDR/kg)
  - ``harga_bawang_merah`` -- Shallot price (IDR/kg)
  - ``harga_telur_ayam`` -- Chicken egg price (IDR/kg)

Design:
  - Daily prices across provinces from Badan Pangan Nasional
  - Critical for inflation nowcasting and BI rate path forecasting
  - Idempotent upsert keyed on (indicator, reference_date, province)
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

PANEL_HARGA_URL = "https://panelharga.badanpangan.go.id/api/v1/harga"
MAX_RETRIES = 3

COMMODITY_CODES: dict[str, str] = {
    "harga_beras_medium": "beras_medium",
    "harga_gula_pasir": "gula_pasir",
    "harga_minyak_goreng": "minyak_goreng",
    "harga_daging_sapi": "daging_sapi",
    "harga_cabai_merah": "cabai_merah",
    "harga_bawang_merah": "bawang_merah",
    "harga_telur_ayam": "telur_ayam",
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


class PanelHargaPanganIngester:
    """Ingester for strategic food prices from Badan Pangan Nasional.

    Fetches daily staple food prices across Indonesian provinces
    for inflation nowcasting and monetary policy analysis.

    Usage::

        ingester = PanelHargaPanganIngester()
        result = await ingester.ingest_for_date_range(
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
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
        commodities: list[str] | None = None,
    ) -> IngestionResult:
        """Ingest food prices over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).
            commodities: Subset of commodity indicators; defaults to all.

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="badan_pangan")
        target = commodities or list(COMMODITY_CODES.keys())

        all_records: list[dict[str, Any]] = []
        for indicator in target:
            try:
                records = await self._fetch_prices(indicator, start, end)
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

        INGESTION_ROWS.labels(source="badan_pangan", symbol="PANGAN", operation="inserted").inc(inserted)

        self._logger.info(
            "panel_harga_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # Data fetch

    async def _fetch_prices(self, indicator: str, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch food prices for a single commodity from Badan Pangan.

        Args:
            indicator: Commodity indicator code.
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised price records by province.

        Raises:
            IngestionError: On fetch failure.
        """
        commodity_code = COMMODITY_CODES.get(indicator)
        if commodity_code is None:
            raise IngestionError(f"Unknown commodity: {indicator}")

        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }
        params = {
            "commodity": commodity_code,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(PANEL_HARGA_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("data", payload if isinstance(payload, list) else [])
                    return [
                        {
                            "indicator": indicator,
                            "reference_date": date.fromisoformat(row["date"][:10]),
                            "value": Decimal(str(row.get("price", row.get("value", 0)))),
                            "unit": "idr_per_kg",
                            "frequency": "daily",
                            "province": row.get("province", "nasional"),
                        }
                        for row in items
                        if row.get("date")
                    ]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"Panel Harga error ({indicator}): {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"Panel Harga connection error: {exc}") from exc

        raise IngestionError(f"Panel Harga {indicator} failed after {MAX_RETRIES} retries")

    # Validation

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a food price record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if v <= 0:
            raise DataQualityError(f"Non-positive price {v} for {record['indicator']} on {record['reference_date']}")
        # Sanity: most staple prices are 5,000-250,000 IDR/kg
        if v > 500000:
            raise DataQualityError(f"Price {v} IDR/kg exceeds plausible max for {record['indicator']}")

    # Persistence

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert food price records into ``alternative_data``.

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
                             :province, 'badan_pangan', NOW())
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
                        "province": rec.get("province", "nasional"),
                    },
                )
                is_insert = result.scalar()
                if is_insert:
                    inserted += 1
                else:
                    updated += 1

        return inserted, updated
