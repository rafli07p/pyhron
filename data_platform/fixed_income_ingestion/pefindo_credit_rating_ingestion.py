"""PEFINDO credit rating history ingestion.

Source: PT Pemeringkat Efek Indonesia (``pefindo.com``)

Indicators:
  - ``pefindo_issuer_rating`` -- Issuer credit rating (idAAA to idD)
  - ``pefindo_bond_rating`` -- Individual bond/sukuk rating
  - ``pefindo_outlook`` -- Rating outlook (stable/positive/negative)

Design:
  - Rating actions (upgrades, downgrades, affirmations) from PEFINDO
  - Mapped to numeric scale for quantitative analysis
  - Critical for corporate bond spread modelling and credit risk
  - Idempotent upsert keyed on (entity_code, rating_type, effective_date)
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

PEFINDO_API_URL = "https://www.pefindo.com/api/v1/ratings"
MAX_RETRIES = 3

# Numeric mapping for PEFINDO rating scale (higher = better)
RATING_SCALE: dict[str, int] = {
    "idAAA": 22,
    "idAA+": 21,
    "idAA": 20,
    "idAA-": 19,
    "idA+": 18,
    "idA": 17,
    "idA-": 16,
    "idBBB+": 15,
    "idBBB": 14,
    "idBBB-": 13,
    "idBB+": 12,
    "idBB": 11,
    "idBB-": 10,
    "idB+": 9,
    "idB": 8,
    "idB-": 7,
    "idCCC": 6,
    "idCC": 5,
    "idC": 4,
    "idSD": 2,
    "idD": 1,
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


class PEFINDOCreditRatingIngester:
    """Ingester for PEFINDO credit rating history.

    Fetches rating actions from PEFINDO including issuer ratings,
    bond ratings, and outlook changes for credit risk analysis.

    Usage::

        ingester = PEFINDOCreditRatingIngester()
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
        """Ingest PEFINDO rating actions over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="pefindo")

        all_records: list[dict[str, Any]] = []

        try:
            records = await self._fetch_ratings(start, end)
            all_records.extend(records)
        except IngestionError as exc:
            result.errors.append(f"PEFINDO fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="pefindo", symbol="RATING", operation="inserted").inc(inserted)

        self._logger.info(
            "pefindo_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # Data fetch

    async def _fetch_ratings(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch rating actions from PEFINDO.

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised rating action records.

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
                    resp = await client.get(PEFINDO_API_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("data", payload if isinstance(payload, list) else [])
                    records: list[dict[str, Any]] = []
                    for row in items:
                        ref = row.get("effective_date", row.get("date", ""))[:10]
                        entity = row.get("entity_code", row.get("issuer", ""))
                        if not ref or not entity:
                            continue
                        ref_date = date.fromisoformat(ref)
                        rating = row.get("rating", "")
                        rating_numeric = RATING_SCALE.get(rating)
                        if rating and rating_numeric is not None:
                            records.append(
                                {
                                    "indicator": "pefindo_issuer_rating",
                                    "entity_code": entity,
                                    "reference_date": ref_date,
                                    "value": Decimal(str(rating_numeric)),
                                    "unit": "rating_score",
                                    "frequency": "event",
                                    "rating_label": rating,
                                    "action": row.get("action", ""),
                                }
                            )
                        outlook = row.get("outlook", "")
                        if outlook:
                            outlook_score = {"positive": 1, "stable": 0, "negative": -1}
                            records.append(
                                {
                                    "indicator": "pefindo_outlook",
                                    "entity_code": entity,
                                    "reference_date": ref_date,
                                    "value": Decimal(str(outlook_score.get(outlook.lower(), 0))),
                                    "unit": "score",
                                    "frequency": "event",
                                    "outlook_label": outlook,
                                }
                            )
                    return records
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"PEFINDO API error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"PEFINDO connection error: {exc}") from exc

        raise IngestionError(f"PEFINDO failed after {MAX_RETRIES} retries")

    # Validation

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a credit rating record.

        Raises:
            DataQualityError: If validation fails.
        """
        if record["indicator"] == "pefindo_issuer_rating":
            v = float(record["value"])
            if v < 1 or v > 22:
                raise DataQualityError(
                    f"Rating score {v} outside valid range [1, 22] for {record.get('entity_code', '?')}"
                )

    # Persistence

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert rating records into ``fixed_income_data``.

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
                            (indicator, entity_code, reference_date, value, unit,
                             frequency, source, updated_at)
                        VALUES
                            (:indicator, :entity_code, :reference_date, :value, :unit,
                             :frequency, 'pefindo', NOW())
                        ON CONFLICT (indicator, entity_code, reference_date) DO UPDATE SET
                            value = EXCLUDED.value,
                            unit = EXCLUDED.unit,
                            source = EXCLUDED.source,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS is_insert
                    """),
                    {
                        "indicator": rec["indicator"],
                        "entity_code": rec.get("entity_code", ""),
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
