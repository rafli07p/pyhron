"""Governance intelligence API endpoints.

Corporate governance flags, ownership changes, and audit opinion
tracking for IDX-listed companies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from datetime import date, datetime

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/governance", tags=["governance"])


# ── Response Models ──────────────────────────────────────────────────────────


class GovernanceFlag(BaseModel):
    id: str
    symbol: str
    flag_type: str = Field(
        description="related_party_txn, board_change, delayed_filing, unusual_audit, insider_trading"
    )
    severity: str = Field(description="low, medium, high, critical")
    title: str
    description: str
    source: str | None = None
    detected_at: datetime
    resolved: bool = False


class OwnershipChange(BaseModel):
    symbol: str
    holder_name: str
    holder_type: str = Field(description="insider, institution, public")
    change_type: str = Field(description="acquisition, disposal, dilution")
    shares_before: int
    shares_after: int
    change_pct: float
    transaction_date: date
    reported_date: date | None = None


class AuditOpinion(BaseModel):
    symbol: str
    fiscal_year: int
    auditor: str
    opinion: str = Field(description="unqualified, qualified, adverse, disclaimer")
    key_audit_matters: list[str] = Field(default_factory=list)
    going_concern: bool = False
    report_date: date | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/flags", response_model=list[GovernanceFlag])
async def get_governance_flags(
    symbol: str | None = Query(None, description="Filter by ticker symbol"),
    severity: str | None = Query(None, pattern="^(low|medium|high|critical)$", description="Min severity"),
    resolved: bool | None = Query(None, description="Filter by resolution status"),
    limit: int = Query(50, ge=1, le=200),
) -> list[GovernanceFlag]:
    """Get governance flags with optional symbol and severity filters."""
    logger.info("governance_flags_queried", symbol=symbol, severity=severity)
    return []


@router.get("/ownership-changes/{symbol}", response_model=list[OwnershipChange])
async def get_ownership_changes(
    symbol: str,
    holder_type: str | None = Query(None, pattern="^(insider|institution|public)$"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[OwnershipChange]:
    """Get ownership change history for a specific stock."""
    logger.info("ownership_changes_queried", symbol=symbol)
    return []


@router.get("/audit-opinions/{symbol}", response_model=list[AuditOpinion])
async def get_audit_opinions(
    symbol: str,
    limit: int = Query(5, ge=1, le=20),
) -> list[AuditOpinion]:
    """Get historical audit opinions for a specific stock."""
    return []
