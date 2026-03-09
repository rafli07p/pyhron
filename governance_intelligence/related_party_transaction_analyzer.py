"""Related party transaction (RPT) analyzer.

Maps Indonesian conglomerate structures and flags material related
party transactions that may indicate governance risks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass
class RelatedPartyTransaction:
    """Detected related party transaction."""

    symbol: str
    counterparty: str
    relationship: str
    transaction_type: str
    value_idr_bn: float
    as_pct_of_equity: float
    event_date: date
    risk_level: str


CONGLOMERATE_MAP: dict[str, list[str]] = {
    "Salim Group": ["INDF", "ICBP", "MPPA"],
    "Astra International": ["ASII", "AALI", "UNTR"],
    "Sinar Mas": ["SMAR", "DSSA", "BSDE"],
    "Lippo Group": ["LPKR", "MNCN", "LPPF"],
    "Bakrie Group": ["BUMI", "BNBR", "ELTY"],
}


class RelatedPartyTransactionAnalyzer:
    """Analyze related party transactions within conglomerate groups."""

    async def detect_rpt_flags(
        self, session: AsyncSession, days: int = 30,
    ) -> list[RelatedPartyTransaction]:
        """Detect flagged RPTs from governance filings.

        Args:
            session: Async database session.
            days: Lookback period.

        Returns:
            List of RPT flags sorted by risk level.
        """
        result = await session.execute(
            text("""
                SELECT symbol, title, description, event_date
                FROM governance.idx_equity_governance_flag
                WHERE flag_type = 'RELATED_PARTY_TRANSACTION'
                  AND event_date >= CURRENT_DATE - :days
                ORDER BY event_date DESC
            """),
            {"days": days},
        )

        flags: list[RelatedPartyTransaction] = []
        for row in result.fetchall():
            flags.append(RelatedPartyTransaction(
                symbol=row[0],
                counterparty=row[2] or "",
                relationship="conglomerate_affiliate",
                transaction_type="material_transaction",
                value_idr_bn=0.0,
                as_pct_of_equity=0.0,
                event_date=row[3],
                risk_level="MEDIUM",
            ))

        logger.info("rpt_flags_detected", count=len(flags))
        return flags

    def get_conglomerate_group(self, symbol: str) -> str | None:
        """Look up conglomerate group for a symbol."""
        for group, members in CONGLOMERATE_MAP.items():
            if symbol in members:
                return group
        return None
