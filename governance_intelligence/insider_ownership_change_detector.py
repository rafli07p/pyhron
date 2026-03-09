"""OJK/IDX insider ownership change detection.

Monitors changes in beneficial ownership of IDX-listed companies
based on OJK (Otoritas Jasa Keuangan) and IDX disclosure filings.
Detects material changes in director, commissioner, and controlling
shareholder positions.

Regulatory basis:
  - OJK Regulation No. 11/2017: Beneficial ownership reporting.
  - IDX Rule I-E: Material information disclosure.
  - Threshold: 5% ownership change triggers mandatory disclosure.

Usage::

    detector = InsiderOwnershipChangeDetector()
    changes = detector.detect_changes(filings)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from datetime import datetime

logger = get_logger(__name__)


class InsiderRole(StrEnum):
    """Role of the insider in the company."""

    DIRECTOR = "DIRECTOR"
    COMMISSIONER = "COMMISSIONER"
    CONTROLLING_SHAREHOLDER = "CONTROLLING_SHAREHOLDER"
    AFFILIATED_PARTY = "AFFILIATED_PARTY"


class ChangeDirection(StrEnum):
    """Direction of ownership change."""

    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    NEW_POSITION = "NEW_POSITION"
    FULL_EXIT = "FULL_EXIT"


@dataclass(frozen=True)
class OwnershipFiling:
    """Single ownership disclosure filing from OJK/IDX.

    Attributes:
        ticker: IDX ticker symbol.
        insider_name: Name of the insider/beneficial owner.
        role: Insider's role in the company.
        shares_before: Share count before the transaction.
        shares_after: Share count after the transaction.
        pct_before: Ownership percentage before.
        pct_after: Ownership percentage after.
        transaction_date: Date of the ownership change.
        filing_date: Date the filing was made.
        source: Filing source (``OJK`` or ``IDX``).
    """

    ticker: str
    insider_name: str
    role: InsiderRole
    shares_before: int
    shares_after: int
    pct_before: float
    pct_after: float
    transaction_date: datetime
    filing_date: datetime
    source: str = "IDX"


@dataclass
class OwnershipChangeAlert:
    """Alert for a material insider ownership change.

    Attributes:
        ticker: IDX ticker symbol.
        insider_name: Name of the insider.
        role: Insider's role.
        direction: Direction of change (increase/decrease/exit).
        shares_changed: Absolute number of shares changed.
        pct_change: Change in ownership percentage.
        pct_after: Ownership percentage after the change.
        materiality: Materiality level (CRITICAL/HIGH/MEDIUM/LOW).
        signal_type: Investment signal interpretation.
        filing: Original filing data.
    """

    ticker: str
    insider_name: str
    role: InsiderRole
    direction: ChangeDirection
    shares_changed: int
    pct_change: float
    pct_after: float
    materiality: str
    signal_type: str
    filing: OwnershipFiling


class InsiderOwnershipChangeDetector:
    """Detect material insider ownership changes from OJK/IDX filings.

    Classifies each ownership change by materiality and generates
    investment signals based on insider trading patterns.

    Args:
        material_threshold_pct: Minimum percentage change for materiality.
        critical_threshold_pct: Percentage change for CRITICAL level.
    """

    def __init__(
        self,
        material_threshold_pct: float = 1.0,
        critical_threshold_pct: float = 5.0,
    ) -> None:
        self._material_threshold = material_threshold_pct
        self._critical_threshold = critical_threshold_pct

        logger.info(
            "ownership_detector_initialised",
            material_threshold=material_threshold_pct,
            critical_threshold=critical_threshold_pct,
        )

    def detect_changes(self, filings: list[OwnershipFiling]) -> list[OwnershipChangeAlert]:
        """Analyse filings and detect material ownership changes.

        Args:
            filings: List of ownership disclosure filings.

        Returns:
            List of OwnershipChangeAlert for material changes.
        """
        alerts: list[OwnershipChangeAlert] = []

        for filing in filings:
            pct_change = filing.pct_after - filing.pct_before
            shares_changed = abs(filing.shares_after - filing.shares_before)

            if filing.shares_before == 0 and filing.shares_after > 0:
                direction = ChangeDirection.NEW_POSITION
            elif filing.shares_after == 0 and filing.shares_before > 0:
                direction = ChangeDirection.FULL_EXIT
            elif pct_change > 0:
                direction = ChangeDirection.INCREASE
            else:
                direction = ChangeDirection.DECREASE

            abs_change = abs(pct_change)
            if abs_change >= self._critical_threshold:
                materiality = "CRITICAL"
            elif abs_change >= self._material_threshold:
                materiality = "HIGH"
            elif abs_change >= 0.5:
                materiality = "MEDIUM"
            else:
                materiality = "LOW"

            signal_type = self._interpret_signal(direction, filing.role, abs_change)

            alert = OwnershipChangeAlert(
                ticker=filing.ticker,
                insider_name=filing.insider_name,
                role=filing.role,
                direction=direction,
                shares_changed=shares_changed,
                pct_change=round(pct_change, 4),
                pct_after=filing.pct_after,
                materiality=materiality,
                signal_type=signal_type,
                filing=filing,
            )
            alerts.append(alert)

            logger.info(
                "ownership_change_detected",
                ticker=filing.ticker,
                insider=filing.insider_name,
                direction=direction.value,
                pct_change=round(pct_change, 4),
                materiality=materiality,
            )

        return alerts

    @staticmethod
    def _interpret_signal(direction: ChangeDirection, role: InsiderRole, abs_change: float) -> str:
        """Interpret ownership change as an investment signal."""
        if direction == ChangeDirection.FULL_EXIT:
            return "BEARISH — insider full exit"
        if direction == ChangeDirection.NEW_POSITION:
            return "BULLISH — new insider position"
        if direction == ChangeDirection.INCREASE:
            if role in (InsiderRole.DIRECTOR, InsiderRole.CONTROLLING_SHAREHOLDER):
                return "BULLISH — director/controller increasing stake"
            return "MILDLY_BULLISH — insider accumulation"
        if abs_change >= 5.0:
            return "BEARISH — significant insider selling"
        return "MILDLY_BEARISH — insider distribution"
