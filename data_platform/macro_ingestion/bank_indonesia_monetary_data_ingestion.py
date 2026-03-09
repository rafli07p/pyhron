"""Bank Indonesia monetary data ingestion.

Source: Bank Indonesia API / Open Data (``bi.go.id``)

Indicators:
  - ``bi_rate`` -- BI-7 Day Reverse Repo Rate
  - ``idr_usd_jisdor`` -- Jakarta Interbank Spot Dollar Rate
  - ``m2_broad_money_idr`` -- Broad money (M2) in IDR
  - ``foreign_exchange_reserves_usd_bn`` -- FX reserves in USD billions
  - ``ikk_consumer_confidence_index`` -- Indeks Keyakinan Konsumen
  - ``bi_lending_rate`` -- Average lending rate
  - ``bi_deposit_rate`` -- Average deposit rate

Design:
  - Each indicator has its own fetch/parse path
  - Idempotent upsert keyed on (indicator, reference_date)
  - Monthly and daily frequencies supported
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

BI_API_BASE = "https://dataapi.bi.go.id/dataapi"
BI_SEKI_URL = "https://www.bi.go.id/id/statistik/ekonomi-keuangan/seki"

INDICATORS: list[str] = [
    "bi_rate",
    "idr_usd_jisdor",
    "m2_broad_money_idr",
    "foreign_exchange_reserves_usd_bn",
    "ikk_consumer_confidence_index",
    "bi_lending_rate",
    "bi_deposit_rate",
]

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


class BankIndonesiaMonetaryDataIngester:
    """Ingester for Bank Indonesia monetary and macro indicators.

    Fetches key monetary indicators from the BI Open Data API and SEKI
    (Statistik Ekonomi dan Keuangan Indonesia) and persists them into
    the ``macro_indicators`` table.

    Usage::

        ingester = BankIndonesiaMonetaryDataIngester()
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
        indicators: list[str] | None = None,
    ) -> IngestionResult:
        """Ingest BI monetary indicators over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).
            indicators: Subset of indicators to fetch; defaults to all.

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="bank_indonesia")
        target = indicators or INDICATORS

        all_records: list[dict[str, Any]] = []
        for indicator in target:
            try:
                records = await self._fetch_indicator(indicator, start, end)
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

        INGESTION_ROWS.labels(source="bank_indonesia", symbol="MACRO", operation="inserted").inc(inserted)

        self._logger.info(
            "bi_monetary_ingestion_complete",
            indicators=target,
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # ── Indicator fetchers ───────────────────────────────────────────────

    async def _fetch_indicator(
        self,
        indicator: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Dispatch to the correct fetcher for *indicator*.

        Args:
            indicator: Indicator code (e.g. ``"bi_rate"``).
            start: Start date filter.
            end: End date filter.

        Returns:
            List of normalised indicator records.

        Raises:
            IngestionError: If the indicator is unknown or fetch fails.
        """
        dispatch = {
            "bi_rate": self._fetch_bi_rate,
            "idr_usd_jisdor": self._fetch_jisdor,
            "m2_broad_money_idr": self._fetch_m2,
            "foreign_exchange_reserves_usd_bn": self._fetch_fx_reserves,
            "ikk_consumer_confidence_index": self._fetch_ikk,
            "bi_lending_rate": self._fetch_lending_rate,
            "bi_deposit_rate": self._fetch_deposit_rate,
        }
        fetcher = dispatch.get(indicator)
        if fetcher is None:
            raise IngestionError(f"Unknown indicator: {indicator}")
        return await fetcher(start, end)

    async def _fetch_bi_rate(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch BI-7DRR (BI Rate) from the BI API.

        Returns:
            Normalised records with indicator='bi_rate'.
        """
        data = await self._bi_api_request(
            "/v1/dataapi/dataview", {"dataset": "bi7drr", "from": start.isoformat(), "to": end.isoformat()}
        )
        return [
            {
                "indicator": "bi_rate",
                "reference_date": date.fromisoformat(row.get("date", row.get("period", ""))[:10]),
                "value": Decimal(str(row.get("value", row.get("rate", 0)))),
                "unit": "percent",
                "frequency": "monthly",
            }
            for row in data
            if row.get("date") or row.get("period")
        ]

    async def _fetch_jisdor(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch JISDOR (IDR/USD fixing) from the BI API.

        Returns:
            Normalised records with indicator='idr_usd_jisdor'.
        """
        data = await self._bi_api_request(
            "/v1/dataapi/dataview", {"dataset": "jisdor", "from": start.isoformat(), "to": end.isoformat()}
        )
        return [
            {
                "indicator": "idr_usd_jisdor",
                "reference_date": date.fromisoformat(row.get("date", "")[:10]),
                "value": Decimal(str(row.get("value", row.get("close", 0)))),
                "unit": "idr_per_usd",
                "frequency": "daily",
            }
            for row in data
            if row.get("date")
        ]

    async def _fetch_m2(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch M2 broad money supply from the BI SEKI dataset.

        Returns:
            Normalised records with indicator='m2_broad_money_idr'.
        """
        data = await self._bi_api_request(
            "/v1/dataapi/dataview", {"dataset": "m2", "from": start.isoformat(), "to": end.isoformat()}
        )
        return [
            {
                "indicator": "m2_broad_money_idr",
                "reference_date": date.fromisoformat(row.get("date", row.get("period", ""))[:10]),
                "value": Decimal(str(row.get("value", 0))),
                "unit": "billion_idr",
                "frequency": "monthly",
            }
            for row in data
            if row.get("date") or row.get("period")
        ]

    async def _fetch_fx_reserves(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch foreign exchange reserves from BI.

        Returns:
            Normalised records with indicator='foreign_exchange_reserves_usd_bn'.
        """
        data = await self._bi_api_request(
            "/v1/dataapi/dataview", {"dataset": "cadev", "from": start.isoformat(), "to": end.isoformat()}
        )
        return [
            {
                "indicator": "foreign_exchange_reserves_usd_bn",
                "reference_date": date.fromisoformat(row.get("date", row.get("period", ""))[:10]),
                "value": Decimal(str(row.get("value", 0))),
                "unit": "billion_usd",
                "frequency": "monthly",
            }
            for row in data
            if row.get("date") or row.get("period")
        ]

    async def _fetch_ikk(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch IKK (consumer confidence index) from BI.

        Returns:
            Normalised records with indicator='ikk_consumer_confidence_index'.
        """
        data = await self._bi_api_request(
            "/v1/dataapi/dataview", {"dataset": "ikk", "from": start.isoformat(), "to": end.isoformat()}
        )
        return [
            {
                "indicator": "ikk_consumer_confidence_index",
                "reference_date": date.fromisoformat(row.get("date", row.get("period", ""))[:10]),
                "value": Decimal(str(row.get("value", 0))),
                "unit": "index",
                "frequency": "monthly",
            }
            for row in data
            if row.get("date") or row.get("period")
        ]

    async def _fetch_lending_rate(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch average lending rate from BI.

        Returns:
            Normalised records with indicator='bi_lending_rate'.
        """
        data = await self._bi_api_request(
            "/v1/dataapi/dataview", {"dataset": "lending_rate", "from": start.isoformat(), "to": end.isoformat()}
        )
        return [
            {
                "indicator": "bi_lending_rate",
                "reference_date": date.fromisoformat(row.get("date", row.get("period", ""))[:10]),
                "value": Decimal(str(row.get("value", 0))),
                "unit": "percent",
                "frequency": "monthly",
            }
            for row in data
            if row.get("date") or row.get("period")
        ]

    async def _fetch_deposit_rate(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch average deposit rate from BI.

        Returns:
            Normalised records with indicator='bi_deposit_rate'.
        """
        data = await self._bi_api_request(
            "/v1/dataapi/dataview", {"dataset": "deposit_rate", "from": start.isoformat(), "to": end.isoformat()}
        )
        return [
            {
                "indicator": "bi_deposit_rate",
                "reference_date": date.fromisoformat(row.get("date", row.get("period", ""))[:10]),
                "value": Decimal(str(row.get("value", 0))),
                "unit": "percent",
                "frequency": "monthly",
            }
            for row in data
            if row.get("date") or row.get("period")
        ]

    # ── HTTP layer ───────────────────────────────────────────────────────

    async def _bi_api_request(
        self,
        path: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Make a request to the BI Data API with retry logic.

        Args:
            path: API endpoint path.
            params: Query parameters.

        Returns:
            Parsed JSON data as list of dicts.

        Raises:
            IngestionError: On persistent failure.
        """
        url = f"{BI_API_BASE}{path}"
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    resp.raise_for_status()
                    payload = resp.json()
                    return payload.get("data", payload if isinstance(payload, list) else [])
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BI API error ({path}): {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"BI connection error ({path}): {exc}") from exc

        raise IngestionError(f"BI API failed after {MAX_RETRIES} retries")

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a macro indicator record.

        Raises:
            DataQualityError: If validation fails.
        """
        if record["indicator"] not in INDICATORS:
            raise DataQualityError(f"Unknown indicator: {record['indicator']}")
        if record["value"] is None:
            raise DataQualityError(f"Null value for {record['indicator']} on {record['reference_date']}")
        # JISDOR sanity: IDR/USD should be between 1,000 and 100,000
        if record["indicator"] == "idr_usd_jisdor":
            v = float(record["value"])
            if v < 1000 or v > 100000:
                raise DataQualityError(f"JISDOR value {v} outside plausible range [1000, 100000]")
        # BI rate sanity: between 0% and 30%
        if record["indicator"] == "bi_rate":
            v = float(record["value"])
            if v < 0 or v > 30:
                raise DataQualityError(f"BI rate {v}% outside plausible range [0, 30]")

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert macro indicator records into ``macro_indicators``.

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
                             'bank_indonesia', NOW())
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
