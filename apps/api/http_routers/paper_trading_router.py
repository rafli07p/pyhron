"""Paper trading API endpoints.

Session lifecycle management, NAV history, P&L attribution,
simulation execution, and reconciliation reporting.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/paper-trading", tags=["paper-trading"])


# ── Request/Response Models ──────────────────────────────────────────────────


class CreatePaperSessionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    strategy_id: UUID
    initial_capital_idr: Decimal = Field(..., gt=0)
    mode: str = Field(default="LIVE_HOURS", pattern="^(LIVE_HOURS|SIMULATION)$")


class PaperSessionResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    strategy_id: UUID
    status: str
    mode: str
    initial_capital_idr: Decimal
    current_nav_idr: Decimal
    peak_nav_idr: Decimal
    max_drawdown_pct: float
    total_trades: int
    winning_trades: int
    realized_pnl_idr: Decimal
    total_commission_idr: Decimal
    cash_idr: Decimal
    unsettled_cash_idr: Decimal
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class PaperNavSnapshotResponse(BaseModel):
    timestamp: datetime
    nav_idr: Decimal
    cash_idr: Decimal
    gross_exposure_idr: Decimal
    drawdown_pct: float
    daily_pnl_idr: Decimal
    daily_return_pct: float


class PaperSessionSummaryResponse(BaseModel):
    session_id: str
    name: str
    initial_capital_idr: Decimal
    final_nav_idr: Decimal
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None
    total_trades: int
    winning_trades: int
    win_rate_pct: float
    total_commission_idr: Decimal
    net_return_after_costs_pct: float
    duration_days: int
    started_at: datetime | None = None
    stopped_at: datetime | None = None


class SimulationRequest(BaseModel):
    date_from: date
    date_to: date
    slippage_bps: Decimal = Field(default=Decimal("10"), ge=0, le=100)


class AttributionReportResponse(BaseModel):
    session_id: str
    date_from: date
    date_to: date
    total_realized_pnl_idr: Decimal
    total_unrealized_pnl_idr: Decimal
    total_commission_idr: Decimal
    total_turnover_idr: Decimal
    total_trades: int
    by_symbol: dict[str, Any] = Field(default_factory=dict)
    by_signal_source: dict[str, Any] = Field(default_factory=dict)


class ReconciliationReportResponse(BaseModel):
    session_id: str
    reconciled_at: datetime
    positions_checked: int
    orders_checked: int
    discrepancies: list[dict[str, Any]] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/sessions", response_model=PaperSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_paper_session(
    request: CreatePaperSessionRequest,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> PaperSessionResponse:
    """Create a new paper trading session."""
    return PaperSessionResponse(
        name=request.name,
        strategy_id=request.strategy_id,
        status="INITIALIZING",
        mode=request.mode,
        initial_capital_idr=request.initial_capital_idr,
        current_nav_idr=request.initial_capital_idr,
        peak_nav_idr=request.initial_capital_idr,
        max_drawdown_pct=0.0,
        total_trades=0,
        winning_trades=0,
        realized_pnl_idr=Decimal("0"),
        total_commission_idr=Decimal("0"),
        cash_idr=request.initial_capital_idr,
        unsettled_cash_idr=Decimal("0"),
    )


@router.post("/sessions/{session_id}/start")
async def start_paper_session(
    session_id: UUID,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> dict[str, str]:
    """Start a paper trading session."""
    return {"status": "started", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/pause")
async def pause_paper_session(
    session_id: UUID,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> dict[str, str]:
    """Pause a running paper trading session."""
    return {"status": "paused", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/resume")
async def resume_paper_session(
    session_id: UUID,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> dict[str, str]:
    """Resume a paused paper trading session."""
    return {"status": "resumed", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/stop", response_model=PaperSessionSummaryResponse)
async def stop_paper_session(
    session_id: UUID,
    close_positions: bool = True,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> PaperSessionSummaryResponse:
    """Stop a paper trading session and return summary."""
    now = datetime.now(tz=UTC)
    return PaperSessionSummaryResponse(
        session_id=str(session_id),
        name="",
        initial_capital_idr=Decimal("0"),
        final_nav_idr=Decimal("0"),
        total_return_pct=0.0,
        max_drawdown_pct=0.0,
        total_trades=0,
        winning_trades=0,
        win_rate_pct=0.0,
        total_commission_idr=Decimal("0"),
        net_return_after_costs_pct=0.0,
        duration_days=0,
        stopped_at=now,
    )


@router.get("/sessions/{session_id}/nav", response_model=list[PaperNavSnapshotResponse])
async def get_nav_history(
    session_id: UUID,
    lookback_hours: int = Query(default=8, ge=1, le=720),
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> list[PaperNavSnapshotResponse]:
    """Get NAV snapshot history."""
    return []


@router.get("/sessions/{session_id}/attribution", response_model=AttributionReportResponse)
async def get_pnl_attribution(
    session_id: UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> AttributionReportResponse:
    """Get P&L attribution report for date range."""
    return AttributionReportResponse(
        session_id=str(session_id),
        date_from=date_from,
        date_to=date_to,
        total_realized_pnl_idr=Decimal("0"),
        total_unrealized_pnl_idr=Decimal("0"),
        total_commission_idr=Decimal("0"),
        total_turnover_idr=Decimal("0"),
        total_trades=0,
    )


@router.post("/sessions/{session_id}/simulate", response_model=PaperSessionSummaryResponse)
async def run_simulation(
    session_id: UUID,
    request: SimulationRequest,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> PaperSessionSummaryResponse:
    """Run a simulation for the given date range."""
    return PaperSessionSummaryResponse(
        session_id=str(session_id),
        name="",
        initial_capital_idr=Decimal("0"),
        final_nav_idr=Decimal("0"),
        total_return_pct=0.0,
        max_drawdown_pct=0.0,
        total_trades=0,
        winning_trades=0,
        win_rate_pct=0.0,
        total_commission_idr=Decimal("0"),
        net_return_after_costs_pct=0.0,
        duration_days=0,
    )


@router.get("/sessions/{session_id}/reconciliation", response_model=ReconciliationReportResponse)
async def get_reconciliation_report(
    session_id: UUID,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> ReconciliationReportResponse:
    """Get latest reconciliation report."""
    return ReconciliationReportResponse(
        session_id=str(session_id),
        reconciled_at=datetime.now(tz=UTC),
        positions_checked=0,
        orders_checked=0,
    )
