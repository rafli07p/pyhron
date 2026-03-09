"""Management track record scorer.

Scores CEO/CFO performance based on historical financial metrics,
corporate actions, governance events, and stock price performance
during their tenure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass
class ManagementScore:
    """Management performance score."""

    symbol: str
    executive_name: str
    role: str
    tenure_start: date
    tenure_years: float
    financial_score: float  # 0-100
    governance_score: float  # 0-100
    stock_performance_score: float  # 0-100
    overall_score: float  # 0-100
    grade: str  # A, B, C, D, F


class ManagementTrackRecordScorer:
    """Score management performance during tenure."""

    WEIGHTS = {
        "financial": 0.40,
        "governance": 0.30,
        "stock_performance": 0.30,
    }

    async def score_management(
        self, session: AsyncSession, symbol: str,
    ) -> list[ManagementScore]:
        """Score current management team for a company.

        Args:
            session: Async database session.
            symbol: IDX ticker symbol.

        Returns:
            List of ManagementScore for current executives.
        """
        # Query governance flags for management-related events
        result = await session.execute(
            text("""
                SELECT filer_name, filer_type, COUNT(*) as events,
                       MIN(event_date) as first_event
                FROM governance.idx_equity_governance_flag
                WHERE symbol = :symbol
                  AND filer_type IN ('DIRECTOR', 'COMMISSIONER', 'CEO', 'CFO')
                GROUP BY filer_name, filer_type
            """),
            {"symbol": symbol},
        )

        scores: list[ManagementScore] = []
        for row in result.fetchall():
            tenure_start = row[3]
            tenure_years = (date.today() - tenure_start).days / 365.25

            # Simplified scoring (production would use detailed metrics)
            financial_score = 70.0
            governance_score = max(0, 100 - row[2] * 10)  # Fewer flags = better
            stock_score = 60.0

            overall = (
                financial_score * self.WEIGHTS["financial"]
                + governance_score * self.WEIGHTS["governance"]
                + stock_score * self.WEIGHTS["stock_performance"]
            )

            grade = self._score_to_grade(overall)

            scores.append(ManagementScore(
                symbol=symbol,
                executive_name=row[0],
                role=row[1],
                tenure_start=tenure_start,
                tenure_years=round(tenure_years, 1),
                financial_score=financial_score,
                governance_score=governance_score,
                stock_performance_score=stock_score,
                overall_score=round(overall, 1),
                grade=grade,
            ))

        logger.info("management_scored", symbol=symbol, executives=len(scores))
        return scores

    @staticmethod
    def _score_to_grade(score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        return "F"
