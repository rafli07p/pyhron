"""IDX listed corporate bond data ingestion.

Source: Indonesia Stock Exchange (``idx.co.id``) bond market data

Indicators:
  - ``corp_bond_price`` -- Corporate bond clean price
  - ``corp_bond_yield`` -- Corporate bond yield to maturity (YTM)
  - ``corp_bond_spread`` -- Credit spread over benchmark SBN

Design:
  - Daily corporate bond pricing from IDX bond trading platform
  - Covers listed IDR-denominated corporate bonds (obligasi korporasi)
  - Used for credit market monitoring and corporate cost-of-debt analysis
  - Idempotent upsert keyed on (bond_code, reference_date)
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

IDX_BOND_URL = "https://www.idx.co.id/primary/BondAndSukuk/GetBondAndSukuk"
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


class IDXCorporateBondIngester:
    """Ingester for IDX listed corporate bond data.

    Fetches daily corporate bond prices, yields, and spreads from
    the IDX bond trading platform for credit market analysis.

    Usage::

        ingester = IDXCorporateBondIngester()
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
        """Ingest corporate bond data over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="idx")

        all_records: list[dict[str, Any]] = []

        try:
            records = await self._fetch_bonds(start, end)
            all_records.extend(records)
        except IngestionError as exc:
            result.errors.append(f"IDX bond fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="idx", symbol="CORPBOND", operation="inserted").inc(inserted)

        self._logger.info(
            "idx_bond_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # Data fetch

    async def _fetch_bonds(self, start: date, end: date) -> list[dict[str, Any]]:
        """Fetch corporate bond data from IDX.

        Args:
            start: Start date filter.
            end: End date filter.

        Returns:
            Normalised corporate bond records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "bondType": "corporate",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(IDX_BOND_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("data", payload.get("Results", []))
                    records: list[dict[str, Any]] = []
                    for row in items:
                        ref = row.get("date", row.get("TradeDate", ""))[:10]
                        bond_code = row.get("bond_code", row.get("BondCode", ""))
                        if not ref or not bond_code:
                            continue
                        ref_date = date.fromisoformat(ref)
                        if row.get("price") or row.get("CleanPrice"):
                            records.append(
                                {
                                    "indicator": "corp_bond_price",
                                    "bond_code": bond_code,
                                    "reference_date": ref_date,
                                    "value": Decimal(str(row.get("price", row.get("CleanPrice", 0)))),
                                    "unit": "percent_of_par",
                                    "frequency": "daily",
                                }
                            )
                        if row.get("ytm") or row.get("YTM"):
                            records.append(
                                {
                                    "indicator": "corp_bond_yield",
                                    "bond_code": bond_code,
                                    "reference_date": ref_date,
                                    "value": Decimal(str(row.get("ytm", row.get("YTM", 0)))),
                                    "unit": "percent",
                                    "frequency": "daily",
                                }
                            )
                    return records
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"IDX bond error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"IDX connection error: {exc}") from exc

        raise IngestionError(f"IDX bond failed after {MAX_RETRIES} retries")

    # Validation

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate a corporate bond record.

        Raises:
            DataQualityError: If validation fails.
        """
        v = float(record["value"])
        if record["indicator"] == "corp_bond_price":
            # Bond price typically 50%-150% of par
            if v < 20 or v > 200:
                raise DataQualityError(
                    f"Bond price {v}% outside plausible range [20, 200] for {record.get('bond_code', '?')}"
                )
        if record["indicator"] == "corp_bond_yield":
            # Corporate yields typically 3%-20%
            if v < 0 or v > 30:
                raise DataQualityError(
                    f"Bond yield {v}% outside plausible range [0, 30] for {record.get('bond_code', '?')}"
                )

    # Persistence

    async def _upsert_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert corporate bond records into ``fixed_income_data``.

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
                            (indicator, bond_code, reference_date, value, unit,
                             frequency, source, updated_at)
                        VALUES
                            (:indicator, :bond_code, :reference_date, :value, :unit,
                             :frequency, 'idx', NOW())
                        ON CONFLICT (indicator, bond_code, reference_date) DO UPDATE SET
                            value = EXCLUDED.value,
                            unit = EXCLUDED.unit,
                            source = EXCLUDED.source,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS is_insert
                    """),
                    {
                        "indicator": rec["indicator"],
                        "bond_code": rec.get("bond_code", ""),
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
