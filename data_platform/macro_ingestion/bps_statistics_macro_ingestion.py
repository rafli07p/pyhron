"""BPS (Badan Pusat Statistik) macroeconomic data ingestion.

Source: BPS Open Data API (``webapi.bps.go.id``)

Indicators:
  - CPI (Consumer Price Index) / inflation
  - GDP (quarterly, expenditure and production approach)
  - Trade balance (exports, imports)
  - Unemployment rate
  - Poverty rate

Design:
  - Uses BPS Web API with API key
  - Monthly CPI, quarterly GDP, monthly trade
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

BPS_API_BASE = "https://webapi.bps.go.id/v1/api"
MAX_RETRIES = 3

# BPS variable IDs for key indicators
BPS_VARIABLES: dict[str, dict[str, Any]] = {
    "cpi_headline": {"var_id": "1710", "unit": "index", "frequency": "monthly"},
    "cpi_yoy_inflation": {"var_id": "1711", "unit": "percent", "frequency": "monthly"},
    "gdp_expenditure_nominal": {"var_id": "1955", "unit": "billion_idr", "frequency": "quarterly"},
    "gdp_expenditure_real": {"var_id": "1956", "unit": "billion_idr", "frequency": "quarterly"},
    "gdp_growth_yoy": {"var_id": "1957", "unit": "percent", "frequency": "quarterly"},
    "exports_fob": {"var_id": "1966", "unit": "million_usd", "frequency": "monthly"},
    "imports_cif": {"var_id": "1967", "unit": "million_usd", "frequency": "monthly"},
    "trade_balance": {"var_id": "1968", "unit": "million_usd", "frequency": "monthly"},
    "unemployment_rate": {"var_id": "529", "unit": "percent", "frequency": "semi_annual"},
    "poverty_rate": {"var_id": "185", "unit": "percent", "frequency": "semi_annual"},
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


class BPSStatisticsMacroIngester:
    """Ingester for BPS macroeconomic statistics.

    Fetches CPI, GDP, trade balance, and other macro indicators from the
    BPS Open Data API and persists them into ``macro_indicators``.

    Usage::

        ingester = BPSStatisticsMacroIngester()
        result = await ingester.ingest_for_date_range(
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )
    """

    def __init__(self) -> None:
        self._config = get_config()
        self._logger = get_logger(__name__)
        self._api_key: str = self._config.bps_api_key

    # ── Public API ───────────────────────────────────────────────────────

    async def ingest_for_date_range(
        self,
        start: date,
        end: date,
        indicators: list[str] | None = None,
    ) -> IngestionResult:
        """Ingest BPS macro statistics over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).
            indicators: Subset of indicator keys; defaults to all.

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="bps")
        target = indicators or list(BPS_VARIABLES.keys())

        all_records: list[dict[str, Any]] = []
        for indicator_key in target:
            try:
                records = await self._fetch_bps_indicator(indicator_key, start, end)
                all_records.extend(records)
            except IngestionError as exc:
                result.errors.append(f"{indicator_key}: {exc}")

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

        INGESTION_ROWS.labels(source="bps", symbol="MACRO", operation="inserted").inc(inserted)

        self._logger.info(
            "bps_ingestion_complete",
            indicators=target,
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_bps_indicator(
        self,
        indicator_key: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch a single BPS indicator via the web API.

        Args:
            indicator_key: Key into ``BPS_VARIABLES``.
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised records.

        Raises:
            IngestionError: On fetch failure or unknown indicator.
        """
        spec = BPS_VARIABLES.get(indicator_key)
        if spec is None:
            raise IngestionError(f"Unknown BPS indicator: {indicator_key}")

        params = {
            "model": "data",
            "domain": "0000",
            "var": spec["var_id"],
            "key": self._api_key,
        }

        data = await self._bps_api_request(params)
        records: list[dict[str, Any]] = []

        for item in data:
            try:
                ref_date = self._parse_bps_period(item.get("tahun", ""), item.get("bulan", ""), spec["frequency"])
            except ValueError:
                continue

            if ref_date < start or ref_date > end:
                continue

            value_str = item.get("data_content") or item.get("value")
            if value_str is None:
                continue

            records.append(
                {
                    "indicator": indicator_key,
                    "reference_date": ref_date,
                    "value": Decimal(str(value_str).replace(",", "").strip()),
                    "unit": spec["unit"],
                    "frequency": spec["frequency"],
                }
            )

        return records

    async def _bps_api_request(
        self,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Make a request to the BPS web API with retry.

        Args:
            params: Query parameters.

        Returns:
            Parsed data list.

        Raises:
            IngestionError: On persistent failure.
        """
        url = f"{BPS_API_BASE}/list"
        headers = {"User-Agent": "Pyhron/1.0 (Data Platform)"}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    resp.raise_for_status()
                    payload = resp.json()
                    result: list[dict[str, Any]] = payload.get("data", payload if isinstance(payload, list) else [])
                    return result
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BPS API error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BPS connection error: {exc}") from exc

        raise IngestionError(f"BPS API failed after {MAX_RETRIES} retries")

    # ── Parsing helpers ──────────────────────────────────────────────────

    @staticmethod
    def _parse_bps_period(
        year_str: str,
        month_str: str,
        frequency: str,
    ) -> date:
        """Parse a BPS period into a reference date.

        Args:
            year_str: Year string (e.g. ``"2024"``).
            month_str: Month or quarter string.
            frequency: One of ``"monthly"``, ``"quarterly"``, ``"semi_annual"``.

        Returns:
            Reference date (first day of the period).

        Raises:
            ValueError: If parsing fails.
        """
        year = int(year_str)
        if frequency == "monthly" and month_str:
            month = int(month_str)
            return date(year, month, 1)
        if frequency == "quarterly" and month_str:
            quarter_map = {"I": 1, "II": 4, "III": 7, "IV": 10, "1": 1, "2": 4, "3": 7, "4": 10}
            month = quarter_map.get(month_str.strip(), 1)
            return date(year, month, 1)
        if frequency == "semi_annual" and month_str:
            half_map = {"I": 1, "II": 7, "1": 1, "2": 7}
            month = half_map.get(month_str.strip(), 1)
            return date(year, month, 1)
        return date(year, 1, 1)

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a BPS macro record.

        Raises:
            DataQualityError: If validation fails.
        """
        if record["indicator"] not in BPS_VARIABLES:
            raise DataQualityError(f"Unknown BPS indicator: {record['indicator']}")
        if record["value"] is None:
            raise DataQualityError(f"Null value for {record['indicator']} on {record['reference_date']}")
        # CPI index should be in [50, 500]
        if record["indicator"] == "cpi_headline":
            v = float(record["value"])
            if v < 50 or v > 500:
                raise DataQualityError(f"CPI headline {v} outside plausible range [50, 500]")

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert macro records into ``macro_indicators``.

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
                            (:indicator, :reference_date, :value, :unit, :frequency, 'bps', NOW())
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
