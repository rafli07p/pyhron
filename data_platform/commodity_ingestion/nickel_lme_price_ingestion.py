"""LME nickel and ANTAM domestic nickel price ingestion.

Source:
  - London Metal Exchange (LME) via API
  - PT ANTAM Tbk domestic nickel price page

Indicators:
  - ``nickel_lme_cash`` -- LME nickel cash settlement (USD/ton)
  - ``nickel_lme_3m`` -- LME nickel 3-month forward (USD/ton)
  - ``nickel_antam_domestic`` -- ANTAM domestic nickel price (IDR/kg)

Design:
  - LME nickel is the global benchmark; ANTAM provides domestic reference
  - Used for IDX mining sector valuation (ANTM, INCO, NCKL, MBMA)
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

LME_API_URL = "https://www.lme.com/api/v1/market-data/nickel"
ANTAM_PRICE_URL = "https://www.antam.com/api/nickel-price"
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


class NickelLMEPriceIngester:
    """Ingester for LME nickel and ANTAM domestic nickel prices.

    Fetches LME cash and 3-month nickel prices alongside ANTAM's
    domestic reference price for the Indonesian nickel market.

    Usage::

        ingester = NickelLMEPriceIngester()
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
        """Ingest nickel prices over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="lme")

        all_records: list[dict[str, Any]] = []

        # LME nickel prices
        try:
            lme = await self._fetch_lme_nickel(start, end)
            all_records.extend(lme)
        except IngestionError as exc:
            result.errors.append(f"LME nickel fetch failed: {exc}")

        # ANTAM domestic prices
        try:
            antam = await self._fetch_antam_domestic(start, end)
            all_records.extend(antam)
        except IngestionError as exc:
            result.errors.append(f"ANTAM fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="lme", symbol="NICKEL", operation="inserted").inc(inserted)

        self._logger.info(
            "nickel_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_lme_nickel(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch LME nickel cash and 3-month prices.

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised LME nickel records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }
        params = {"from": start.isoformat(), "to": end.isoformat()}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(LME_API_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("data", payload if isinstance(payload, list) else [])
                    records: list[dict[str, Any]] = []
                    for row in items:
                        ref = row.get("date", "")[:10]
                        if not ref:
                            continue
                        ref_date = date.fromisoformat(ref)
                        if row.get("cash"):
                            records.append(
                                {
                                    "indicator": "nickel_lme_cash",
                                    "reference_date": ref_date,
                                    "value": Decimal(str(row["cash"])),
                                    "unit": "usd_per_ton",
                                    "frequency": "daily",
                                }
                            )
                        if row.get("three_month"):
                            records.append(
                                {
                                    "indicator": "nickel_lme_3m",
                                    "reference_date": ref_date,
                                    "value": Decimal(str(row["three_month"])),
                                    "unit": "usd_per_ton",
                                    "frequency": "daily",
                                }
                            )
                    return records
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"LME nickel error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"LME connection error: {exc}") from exc

        raise IngestionError(f"LME nickel failed after {MAX_RETRIES} retries")

    async def _fetch_antam_domestic(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch ANTAM domestic nickel prices.

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised ANTAM nickel records.

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
                    resp = await client.get(ANTAM_PRICE_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("data", payload if isinstance(payload, list) else [])
                    return [
                        {
                            "indicator": "nickel_antam_domestic",
                            "reference_date": date.fromisoformat(row["date"][:10]),
                            "value": Decimal(str(row.get("price", row.get("value", 0)))),
                            "unit": "idr_per_kg",
                            "frequency": "daily",
                        }
                        for row in items
                        if row.get("date")
                    ]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ANTAM API error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ANTAM connection error: {exc}") from exc

        raise IngestionError(f"ANTAM fetch failed after {MAX_RETRIES} retries")

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a nickel price record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if v <= 0:
            raise DataQualityError(f"Non-positive nickel price {v} on {record['reference_date']}")
        # LME nickel historically ~5000-50000 USD/ton
        if record["unit"] == "usd_per_ton" and (v < 3000 or v > 60000):
            raise DataQualityError(f"Nickel price {v} USD/ton outside plausible range [3000, 60000]")

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert nickel price records into ``commodity_prices``.

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
                            (:indicator, :reference_date, :value, :unit, :frequency, 'lme', NOW())
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
