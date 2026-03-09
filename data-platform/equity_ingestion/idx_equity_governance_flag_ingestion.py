"""IDX Equity Governance Flag ingestion.

Sources: OJK (Otoritas Jasa Keuangan) and IDX disclosures.

Design:
  - Tracks ownership changes (beneficial ownership > 5 %)
  - Tracks audit opinion flags (going concern, qualified)
  - Idempotent upsert keyed on (symbol, flag_type, flag_date)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import httpx
from sqlalchemy import text

from shared.configuration_settings import get_config
from shared.async_database_session import get_session
from shared.platform_exception_hierarchy import (
    DataQualityError,
    IngestionError,
)
from shared.structured_json_logger import get_logger
from shared.prometheus_metrics_registry import INGESTION_ROWS

logger = get_logger(__name__)

OJK_DISCLOSURE_URL = "https://www.ojk.go.id/id/kanal/pasar-modal/data-dan-statistik"
IDX_DISCLOSURE_URL = "https://www.idx.co.id/primary/Disclosure/GetDisclosure"

FLAG_TYPES: list[str] = [
    "ownership_change",
    "audit_going_concern",
    "audit_qualified",
    "related_party_transaction",
    "board_change",
]


@dataclass
class IngestionResult:
    """Outcome of an ingestion run."""

    source: str
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class IDXEquityGovernanceFlagIngester:
    """Governance-flag ingester for IDX equities.

    Monitors ownership changes, audit flags, and other governance-related
    disclosures from the OJK and IDX websites.

    Usage::

        ingester = IDXEquityGovernanceFlagIngester()
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
        symbols: list[str] | None = None,
    ) -> IngestionResult:
        """Ingest governance flags for the given date range.

        Args:
            start: First calendar date (inclusive).
            end: Last calendar date (inclusive).
            symbols: Optional filter for specific tickers.

        Returns:
            An ``IngestionResult`` summarising the run.
        """
        t0 = time.monotonic()
        result = IngestionResult(source="idx_ojk")

        flags: list[dict[str, Any]] = []

        # Fetch from IDX disclosures
        try:
            idx_flags = await self._fetch_idx_disclosures(start, end, symbols)
            flags.extend(idx_flags)
        except IngestionError as exc:
            result.errors.append(f"IDX disclosure fetch failed: {exc}")

        # Fetch from OJK
        try:
            ojk_flags = await self._fetch_ojk_ownership_changes(start, end, symbols)
            flags.extend(ojk_flags)
        except IngestionError as exc:
            result.errors.append(f"OJK fetch failed: {exc}")

        valid: list[dict[str, Any]] = []
        for flag in flags:
            try:
                self._validate_flag(flag)
                valid.append(flag)
            except DataQualityError as exc:
                result.errors.append(str(exc))
                result.rows_skipped += 1

        inserted, updated = await self._upsert_flags(valid)
        result.rows_inserted = inserted
        result.rows_updated = updated
        result.duration_ms = (time.monotonic() - t0) * 1000

        INGESTION_ROWS.labels(
            source="idx_ojk", symbol="GOVERNANCE", operation="inserted"
        ).inc(inserted)

        self._logger.info(
            "governance_flag_ingestion_complete",
            rows_inserted=inserted,
            rows_updated=updated,
            errors=len(result.errors),
            duration_ms=round(result.duration_ms, 2),
        )
        return result

    # ── Data fetch ───────────────────────────────────────────────────────

    async def _fetch_idx_disclosures(
        self,
        start: date,
        end: date,
        symbols: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch governance-related disclosures from IDX.

        Args:
            start: Start date filter.
            end: End date filter.
            symbols: Optional symbol filter.

        Returns:
            List of normalised governance flag dicts.

        Raises:
            IngestionError: On fetch failure.
        """
        params: dict[str, str] = {
            "indexFrom": "0",
            "pageSize": "100",
            "dateFrom": start.isoformat(),
            "dateTo": end.isoformat(),
            "language": "en-us",
        }
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    IDX_DISCLOSURE_URL, params=params, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise IngestionError(f"IDX disclosure API error: {exc}") from exc
        except httpx.RequestError as exc:
            raise IngestionError(f"IDX connection error: {exc}") from exc

        flags: list[dict[str, Any]] = []
        for item in data.get("data", []):
            symbol = (item.get("KodeEmiten") or "").strip().upper()
            if symbols and symbol not in symbols:
                continue

            flag_type = self._classify_disclosure(item)
            if flag_type is None:
                continue

            try:
                flag_date = date.fromisoformat(
                    item.get("TanggalPenyampaian", "")[:10]
                )
            except ValueError:
                continue

            flags.append(
                {
                    "symbol": symbol,
                    "flag_type": flag_type,
                    "flag_date": flag_date,
                    "description": item.get("Perihal", ""),
                    "source": "idx",
                }
            )

        return flags

    async def _fetch_ojk_ownership_changes(
        self,
        start: date,
        end: date,
        symbols: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch ownership-change data from OJK.

        Args:
            start: Start date filter.
            end: End date filter.
            symbols: Optional symbol filter.

        Returns:
            List of normalised governance flag dicts.

        Raises:
            IngestionError: On fetch failure.
        """
        headers = {
            "User-Agent": "Pyhron/1.0 (Data Platform)",
            "Accept": "text/html,application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(OJK_DISCLOSURE_URL, headers=headers)
                resp.raise_for_status()
                html_content = resp.text
        except httpx.HTTPStatusError as exc:
            raise IngestionError(f"OJK API error: {exc}") from exc
        except httpx.RequestError as exc:
            raise IngestionError(f"OJK connection error: {exc}") from exc

        return self._parse_ojk_ownership_html(html_content, start, end, symbols)

    # ── Parsing helpers ──────────────────────────────────────────────────

    def _classify_disclosure(self, item: dict[str, Any]) -> str | None:
        """Classify an IDX disclosure into a governance flag type.

        Args:
            item: Raw disclosure record from IDX API.

        Returns:
            Flag type string or ``None`` if not governance-related.
        """
        subject = (item.get("Perihal") or "").lower()
        if "kepemilikan" in subject or "ownership" in subject:
            return "ownership_change"
        if "going concern" in subject:
            return "audit_going_concern"
        if "wajar dengan pengecualian" in subject or "qualified" in subject:
            return "audit_qualified"
        if "transaksi afiliasi" in subject or "related party" in subject:
            return "related_party_transaction"
        if "direksi" in subject or "komisaris" in subject or "board" in subject:
            return "board_change"
        return None

    def _parse_ojk_ownership_html(
        self,
        html_content: str,
        start: date,
        end: date,
        symbols: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Parse OJK ownership data from HTML content.

        Args:
            html_content: Raw HTML from OJK website.
            start: Start date filter.
            end: End date filter.
            symbols: Optional symbol filter.

        Returns:
            List of normalised ownership change dicts.
        """
        # Placeholder: real implementation would use lxml or selectolax
        # to parse ownership-change tables from OJK disclosure pages.
        self._logger.info("ojk_html_parsing", content_length=len(html_content))
        return []

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_flag(self, flag: dict[str, Any]) -> None:
        """Validate a governance flag record.

        Raises:
            DataQualityError: If validation fails.
        """
        if not flag.get("symbol"):
            raise DataQualityError("Empty symbol in governance flag")
        if flag["flag_type"] not in FLAG_TYPES:
            raise DataQualityError(
                f"Unknown flag type '{flag['flag_type']}'"
            )
        if not flag.get("flag_date"):
            raise DataQualityError(
                f"Missing flag_date for {flag['symbol']}/{flag['flag_type']}"
            )

    # ── Persistence ──────────────────────────────────────────────────────

    async def _upsert_flags(
        self,
        flags: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Upsert governance flags into ``equity_governance_flags``.

        Returns:
            Tuple of (inserted, updated) counts.
        """
        if not flags:
            return 0, 0

        inserted = 0
        updated = 0

        async with get_session() as session:
            for flag in flags:
                result = await session.execute(
                    text("""
                        INSERT INTO equity_governance_flags
                            (symbol, flag_type, flag_date, description, source, updated_at)
                        VALUES
                            (:symbol, :flag_type, :flag_date, :description, :source, NOW())
                        ON CONFLICT (symbol, flag_type, flag_date) DO UPDATE SET
                            description = EXCLUDED.description,
                            source = EXCLUDED.source,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS is_insert
                    """),
                    {
                        "symbol": flag["symbol"],
                        "flag_type": flag["flag_type"],
                        "flag_date": flag["flag_date"],
                        "description": flag.get("description", ""),
                        "source": flag.get("source", "unknown"),
                    },
                )
                is_insert = result.scalar()
                if is_insert:
                    inserted += 1
                else:
                    updated += 1

        return inserted, updated
