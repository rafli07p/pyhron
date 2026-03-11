"""Share pledge risk monitor.

Tracks director and commissioner share pledges which can indicate
forced selling risk if stock price declines trigger margin calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


@dataclass
class SharePledgeRisk:
    """Share pledge risk assessment."""

    symbol: str
    pledgor_name: str
    pledgor_role: str
    shares_pledged: int
    total_shares_owned: int
    pledge_ratio_pct: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL


class SharePledgeRiskMonitor:
    """Monitor share pledge risks from governance filings."""

    async def get_active_pledges(
        self,
        session: AsyncSession,
    ) -> list[SharePledgeRisk]:
        """Get all active share pledges with risk assessment.

        Args:
            session: Async database session.

        Returns:
            List of SharePledgeRisk sorted by risk level.
        """
        result = await session.execute(
            text("""
                SELECT symbol, filer_name, filer_type,
                       shares_before, shares_after, change_pct
                FROM governance_flags
                WHERE flag_type = 'SHARE_PLEDGE'
                  AND severity IN ('HIGH', 'CRITICAL')
                ORDER BY event_date DESC
            """),
        )

        pledges: list[SharePledgeRisk] = []
        for row in result.fetchall():
            pledge_ratio = abs(float(row[5])) if row[5] else 0.0
            risk = self._assess_risk(pledge_ratio)
            pledges.append(
                SharePledgeRisk(
                    symbol=row[0],
                    pledgor_name=row[1] or "",
                    pledgor_role=row[2] or "",
                    shares_pledged=abs(row[3] or 0),
                    total_shares_owned=row[4] or 0,
                    pledge_ratio_pct=pledge_ratio,
                    risk_level=risk,
                )
            )

        pledges.sort(key=lambda p: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(p.risk_level), reverse=True)
        logger.info("pledge_risks_assessed", total=len(pledges))
        return pledges

    @staticmethod
    def _assess_risk(pledge_ratio: float) -> str:
        """Assess pledge risk based on ratio of pledged shares."""
        if pledge_ratio >= 50:
            return "CRITICAL"
        if pledge_ratio >= 30:
            return "HIGH"
        if pledge_ratio >= 15:
            return "MEDIUM"
        return "LOW"
