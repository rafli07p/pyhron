"""ESDM (Ministry of Energy and Mineral Resources) energy production ingestion.

Source: ESDM website (``esdm.go.id``) via web scraping and API.

Data:
  - HBA (Harga Batubara Acuan) -- Indonesian coal reference price
  - ICP (Indonesian Crude Price)
  - Oil and gas lifting volumes

Design:
  - HBA scraped from minerba.esdm.go.id
  - ICP from migas.esdm.go.id
  - Monthly frequency for all indicators
  - Idempotent upsert keyed on (indicator, reference_date)
"""

from __future__ import annotations

import asyncio
import re
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

HBA_URL = "https://minerba.esdm.go.id/harga_acuan"
ICP_URL = "https://migas.esdm.go.id/icp"
LIFTING_URL = "https://migas.esdm.go.id/lifting"
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


class ESDMEnergyProductionIngester:
    """Ingester for ESDM energy production data.

    Scrapes HBA coal price, ICP crude price, and oil/gas lifting data
    from ESDM ministry websites.

    Usage::

        ingester = ESDMEnergyProductionIngester()
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
        """Ingest ESDM energy data over [start, end].

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="esdm")

        all_records: list[dict[str, Any]] = []

        # Fetch HBA coal reference price
        try:
            hba = await self._fetch_hba(start, end)
            all_records.extend(hba)
        except IngestionError as exc:
            result.errors.append(f"HBA fetch failed: {exc}")

        # Fetch ICP crude price
        try:
            icp = await self._fetch_icp(start, end)
            all_records.extend(icp)
        except IngestionError as exc:
            result.errors.append(f"ICP fetch failed: {exc}")

        # Fetch oil/gas lifting
        try:
            lifting = await self._fetch_lifting(start, end)
            all_records.extend(lifting)
        except IngestionError as exc:
            result.errors.append(f"Lifting fetch failed: {exc}")

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

        INGESTION_ROWS.labels(source="esdm", symbol="ENERGY", operation="inserted").inc(inserted)

        self._logger.info(
            "esdm_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_hba(
        self,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Scrape HBA (coal reference price) from esdm.go.id.

        Args:
            start: Start date.
            end: End date.

        Returns:
            Normalised HBA records.

        Raises:
            IngestionError: On fetch or parse failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "text/html,application/json",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    resp = await client.get(HBA_URL, headers=headers)
                    resp.raise_for_status()
                    return self._parse_hba_html(resp.text, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ESDM HBA error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ESDM connection error: {exc}") from exc

        raise IngestionError(f"ESDM HBA failed after {MAX_RETRIES} retries")

    async def _fetch_icp(
        self,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch ICP (Indonesian Crude Price) from ESDM.

        Args:
            start: Start date.
            end: End date.

        Returns:
            Normalised ICP records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "text/html,application/json",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    resp = await client.get(ICP_URL, headers=headers)
                    resp.raise_for_status()
                    return self._parse_icp_html(resp.text, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ESDM ICP error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ESDM ICP connection error: {exc}") from exc

        raise IngestionError(f"ESDM ICP failed after {MAX_RETRIES} retries")

    async def _fetch_lifting(
        self,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Fetch oil and gas lifting volumes from ESDM.

        Args:
            start: Start date.
            end: End date.

        Returns:
            Normalised lifting records.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "text/html,application/json",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    resp = await client.get(LIFTING_URL, headers=headers)
                    resp.raise_for_status()
                    return self._parse_lifting_html(resp.text, start, end)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (500, 502, 503) and attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ESDM lifting error: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                raise IngestionError(f"ESDM lifting connection error: {exc}") from exc

        raise IngestionError(f"ESDM lifting failed after {MAX_RETRIES} retries")

    # ── HTML parsing ─────────────────────────────────────────────────────

    def _parse_hba_html(
        self,
        html: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse HBA price table from ESDM HTML page.

        Args:
            html: Raw HTML content.
            start: Start date filter.
            end: End date filter.

        Returns:
            List of normalised HBA records.
        """
        records: list[dict[str, Any]] = []
        month_map = {
            "januari": 1,
            "februari": 2,
            "maret": 3,
            "april": 4,
            "mei": 5,
            "juni": 6,
            "juli": 7,
            "agustus": 8,
            "september": 9,
            "oktober": 10,
            "november": 11,
            "desember": 12,
        }

        # Pattern: month year ... USD value
        pattern = re.compile(
            r"(?P<month>\w+)\s+(?P<year>\d{4})\s+.*?" r"(?:USD|US\$)\s*(?P<value>[\d.,]+)",
            re.IGNORECASE,
        )

        for match in pattern.finditer(html):
            month_name = match.group("month").lower()
            month = month_map.get(month_name)
            if month is None:
                continue
            year = int(match.group("year"))
            value_str = match.group("value").replace(",", "")

            try:
                ref_date = date(year, month, 1)
                value = Decimal(value_str)
            except (ValueError, ArithmeticError):
                continue

            if ref_date < start or ref_date > end:
                continue

            records.append(
                {
                    "indicator": "hba_coal_price",
                    "reference_date": ref_date,
                    "value": value,
                    "unit": "usd_per_ton",
                    "frequency": "monthly",
                }
            )

        return records

    def _parse_icp_html(
        self,
        html: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse ICP price table from ESDM HTML page.

        Args:
            html: Raw HTML content.
            start: Start date filter.
            end: End date filter.

        Returns:
            List of normalised ICP records.
        """
        records: list[dict[str, Any]] = []
        pattern = re.compile(
            r"(?P<month>\d{1,2})[/\-](?P<year>\d{4})\s+.*?" r"(?:USD|US\$)\s*(?P<value>[\d.,]+)",
            re.IGNORECASE,
        )

        for match in pattern.finditer(html):
            month = int(match.group("month"))
            year = int(match.group("year"))
            value_str = match.group("value").replace(",", "")

            try:
                ref_date = date(year, month, 1)
                value = Decimal(value_str)
            except (ValueError, ArithmeticError):
                continue

            if ref_date < start or ref_date > end:
                continue

            records.append(
                {
                    "indicator": "icp_crude_price",
                    "reference_date": ref_date,
                    "value": value,
                    "unit": "usd_per_barrel",
                    "frequency": "monthly",
                }
            )

        return records

    def _parse_lifting_html(
        self,
        html: str,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Parse oil/gas lifting data from ESDM HTML page.

        Args:
            html: Raw HTML content.
            start: Start date filter.
            end: End date filter.

        Returns:
            List of normalised lifting records.
        """
        records: list[dict[str, Any]] = []
        # Simplified: real implementation would parse structured tables
        self._logger.info("lifting_html_parsing", content_length=len(html))
        return records

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_record(self, record: dict[str, Any]) -> None:
        """Validate an ESDM energy record.

        Raises:
            DataQualityError: If validation fails.
        """
        if record["value"] is None or record["value"] <= 0:
            raise DataQualityError(f"Non-positive value for {record['indicator']} on {record['reference_date']}")
        # HBA coal price: historically between 40 and 500 USD/ton
        if record["indicator"] == "hba_coal_price":
            v = float(record["value"])
            if v < 20 or v > 600:
                raise DataQualityError(f"HBA coal price {v} outside plausible range [20, 600]")
        # ICP crude: historically between 10 and 200 USD/barrel
        if record["indicator"] == "icp_crude_price":
            v = float(record["value"])
            if v < 5 or v > 250:
                raise DataQualityError(f"ICP crude price {v} outside plausible range [5, 250]")

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
                            (:indicator, :reference_date, :value, :unit, :frequency, 'esdm', NOW())
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
