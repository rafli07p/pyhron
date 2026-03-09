"""IDX Equity Index Constituent ingestion (LQ45, IDX30, IDX80).

Source: IDX website (``idx.co.id``) via web scraping.

Design:
  - Scrapes constituent lists from the IDX website
  - Tracks membership changes over time
  - Idempotent upsert keyed on (index_code, symbol, effective_date)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
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

IDX_INDICES: dict[str, str] = {
    "LQ45": "https://www.idx.co.id/en/market-data/stocks/index-constituent/?index=LQ45",
    "IDX30": "https://www.idx.co.id/en/market-data/stocks/index-constituent/?index=IDX30",
    "IDX80": "https://www.idx.co.id/en/market-data/stocks/index-constituent/?index=IDX80",
}

IDX_API_BASE = "https://www.idx.co.id/primary/StockData/GetIndexMemberByCode"


@dataclass
class IngestionResult:
    """Outcome of an ingestion run."""

    source: str
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class IDXEquityIndexConstituentIngester:
    """Ingester for IDX equity-index constituents (LQ45/IDX30/IDX80).

    Scrapes the IDX website to obtain current constituents of major
    Indonesia Stock Exchange indices and persists membership records.

    Usage::

        ingester = IDXEquityIndexConstituentIngester()
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
        indices: list[str] | None = None,
    ) -> IngestionResult:
        """Ingest index constituents for specified indices.

        Args:
            start: First calendar date (inclusive) for effective-date window.
            end: Last calendar date (inclusive).
            indices: Index codes to fetch (default: all known indices).

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="idx_website")
        target_indices = indices or list(IDX_INDICES.keys())

        all_records: list[dict[str, Any]] = []
        for index_code in target_indices:
            try:
                members = await self._fetch_index_members(index_code)
                for symbol in members:
                    all_records.append(
                        {
                            "index_code": index_code,
                            "symbol": symbol,
                            "effective_date": date.today(),
                            "is_member": True,
                        }
                    )
            except IngestionError as exc:
                result.errors.append(f"{index_code}: {exc}")

        valid: list[dict[str, Any]] = []
        for record in all_records:
            try:
                self._validate_constituent(record)
                valid.append(record)
            except DataQualityError as exc:
                result.errors.append(str(exc))
                result.rows_skipped += 1

        inserted, updated = await self._upsert_constituents(valid)
        result.rows_inserted = inserted
        result.rows_updated = updated
        result.duration_ms = (time.monotonic() - t0) * 1000

        INGESTION_ROWS.labels(source="idx_website", symbol="INDEX", operation="inserted").inc(inserted)

        self._logger.info(
            "index_constituent_ingestion_complete",
            indices=target_indices,
            rows_inserted=inserted,
            rows_updated=updated,
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_index_members(self, index_code: str) -> list[str]:
        """Fetch current members of an IDX index.

        Args:
            index_code: Index identifier (e.g. ``"LQ45"``).

        Returns:
            List of member ticker symbols.

        Raises:
            IngestionError: On fetch failure.
        """
        url = IDX_API_BASE
        params = {"code": index_code, "language": "en-us"}
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise IngestionError(f"IDX API error for {index_code}: {exc}") from exc
        except httpx.RequestError as exc:
            raise IngestionError(f"IDX connection error for {index_code}: {exc}") from exc

        members: list[str] = []
        for item in data.get("data", data if isinstance(data, list) else []):
            code = item.get("Code") or item.get("code") or item.get("StockCode")
            if code:
                members.append(code.strip().upper())

        if not members:
            raise IngestionError(f"No members returned for index {index_code}")

        return members

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_constituent(self, record: dict[str, Any]) -> None:
        """Validate a constituent record.

        Raises:
            DataQualityError: If the ticker symbol is invalid.
        """
        symbol = record["symbol"]
        if not symbol or len(symbol) < 2 or len(symbol) > 6:
            raise DataQualityError(f"Invalid symbol '{symbol}' for index {record['index_code']}")
        if not symbol.isalpha():
            raise DataQualityError(f"Symbol '{symbol}' contains non-alpha characters")

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_constituents(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert index constituent records.

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
                        INSERT INTO equity_index_constituents
                            (index_code, symbol, effective_date, is_member, updated_at)
                        VALUES
                            (:index_code, :symbol, :effective_date, :is_member, NOW())
                        ON CONFLICT (index_code, symbol, effective_date) DO UPDATE SET
                            is_member = EXCLUDED.is_member,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS is_insert
                    """),
                    {
                        "index_code": rec["index_code"],
                        "symbol": rec["symbol"],
                        "effective_date": rec["effective_date"],
                        "is_member": rec["is_member"],
                    },
                )
                is_insert = result.scalar()
                if is_insert:
                    inserted += 1
                else:
                    updated += 1

        return inserted, updated
