"""Audit opinion tracker.

Tracks auditor opinions on financial statements: Wajar Tanpa
Pengecualian (unqualified), qualified, adverse, and disclaimer.
Flags companies with non-standard audit opinions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import text

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class AuditOpinion(StrEnum):
    """Indonesian audit opinion types."""

    WTP = "wajar_tanpa_pengecualian"  # Unqualified
    WDP = "wajar_dengan_pengecualian"  # Qualified
    ADVERSE = "tidak_wajar"  # Adverse
    DISCLAIMER = "tidak_memberikan_pendapat"  # Disclaimer


@dataclass
class AuditOpinionRecord:
    """Audit opinion for a company-year."""

    symbol: str
    fiscal_year: int
    auditor: str
    opinion: AuditOpinion
    is_going_concern: bool
    key_audit_matters: list[str]
    report_date: date


class AuditOpinionTracker:
    """Track and flag non-standard audit opinions."""

    async def get_flagged_opinions(
        self,
        session: AsyncSession,
        fiscal_year: int | None = None,
    ) -> list[AuditOpinionRecord]:
        """Get companies with non-WTP audit opinions.

        Args:
            session: Async database session.
            fiscal_year: Target fiscal year. Defaults to current year - 1.

        Returns:
            List of non-standard audit opinions.
        """
        target_year = fiscal_year or (date.today().year - 1)

        result = await session.execute(
            text("""
                SELECT symbol, title, description, event_date
                FROM governance.idx_equity_governance_flag
                WHERE flag_type = 'AUDIT_OPINION'
                  AND EXTRACT(YEAR FROM event_date) = :year
                  AND severity IN ('HIGH', 'CRITICAL')
                ORDER BY event_date DESC
            """),
            {"year": target_year},
        )

        records: list[AuditOpinionRecord] = []
        for row in result.fetchall():
            records.append(
                AuditOpinionRecord(
                    symbol=row[0],
                    fiscal_year=target_year,
                    auditor="",
                    opinion=AuditOpinion.WDP,
                    is_going_concern="going_concern" in (row[2] or "").lower(),
                    key_audit_matters=[],
                    report_date=row[3],
                )
            )

        logger.info("flagged_opinions", year=target_year, count=len(records))
        return records
