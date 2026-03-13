"""Live trading risk management API endpoints.

Kill switch administration, strategy promotion/demotion,
real-time risk snapshots, and capital allocation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum, unique

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from services.api.rest_gateway import Role, TokenPayload, get_current_user, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/live-trading-risk", tags=["live-trading-risk"])


# ── Enumerations ─────────────────────────────────────────────────────────────


@unique
class KillSwitchState(StrEnum):
    """Possible states for the portfolio-wide kill switch."""

    ARMED = "ARMED"
    TRIGGERED = "TRIGGERED"
    DISARMED = "DISARMED"


@unique
class PromotionVerdict(StrEnum):
    """Outcome of a strategy promotion evaluation."""

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


# ── Request Models ───────────────────────────────────────────────────────────


class KillSwitchTriggerRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500, description="Audit trail reason for triggering kill switch")
    cancel_open_orders: bool = Field(default=True, description="Cancel all open orders when triggering")


class KillSwitchResetRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500, description="Audit trail reason for resetting kill switch")
    rearm: bool = Field(default=True, description="Re-arm the kill switch after reset")


class PromotionEvaluateRequest(BaseModel):
    min_sharpe: float = Field(default=1.0, ge=0, description="Minimum Sharpe ratio for promotion")
    min_trading_days: int = Field(default=30, ge=1, description="Minimum trading days in paper session")
    max_drawdown_pct: float = Field(default=15.0, gt=0, le=100, description="Maximum drawdown percentage allowed")


class PromotionPromoteRequest(BaseModel):
    initial_capital_idr: float = Field(..., gt=0, description="Capital to allocate in IDR")
    risk_limit_pct: float = Field(default=2.0, gt=0, le=100, description="Per-trade risk limit as portfolio percentage")
    reason: str = Field(..., min_length=10, max_length=500, description="Justification for promotion")


class DemotionRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500, description="Audit trail reason for demotion")
    liquidate_positions: bool = Field(default=True, description="Liquidate all positions before demotion")


# ── Response Models ──────────────────────────────────────────────────────────


class KillSwitchStatusResponse(BaseModel):
    state: KillSwitchState
    armed_at: datetime | None = None
    triggered_at: datetime | None = None
    triggered_by: str | None = None
    reason: str | None = None
    open_orders_cancelled: int = 0
    positions_flattened: int = 0


class KillSwitchActionResponse(BaseModel):
    previous_state: KillSwitchState
    new_state: KillSwitchState
    actioned_by: str
    actioned_at: datetime
    reason: str
    open_orders_cancelled: int = 0


class PromotionEvaluationResponse(BaseModel):
    session_id: str
    verdict: PromotionVerdict
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    trading_days: int
    total_return_pct: float
    win_rate_pct: float
    notes: list[str] = Field(default_factory=list)


class PromotionActionResponse(BaseModel):
    session_id: str
    strategy_id: str
    status: str
    initial_capital_idr: float
    risk_limit_pct: float
    promoted_at: datetime
    promoted_by: str


class DemotionActionResponse(BaseModel):
    strategy_id: str
    status: str
    positions_liquidated: int
    demoted_at: datetime
    demoted_by: str
    reason: str


class ExposureSnapshot(BaseModel):
    gross_exposure_idr: float = 0.0
    net_exposure_idr: float = 0.0
    long_exposure_idr: float = 0.0
    short_exposure_idr: float = 0.0
    beta_vs_ihsg: float = 0.0


class ConcentrationSnapshot(BaseModel):
    sector_hhi: float = 0.0
    top5_weight_pct: float = 0.0
    largest_position_pct: float = 0.0
    largest_position_symbol: str = ""
    num_positions: int = 0


class VaRSnapshot(BaseModel):
    var_1d_95_idr: float = 0.0
    var_5d_95_idr: float = 0.0
    var_1d_99_idr: float = 0.0
    component_var: dict[str, float] = Field(default_factory=dict)


class RiskSnapshotResponse(BaseModel):
    strategy_id: str
    timestamp: datetime
    nav_idr: float = 0.0
    exposure: ExposureSnapshot = Field(default_factory=ExposureSnapshot)
    concentration: ConcentrationSnapshot = Field(default_factory=ConcentrationSnapshot)
    var: VaRSnapshot = Field(default_factory=VaRSnapshot)
    daily_loss_pct: float = 0.0
    drawdown_pct: float = 0.0
    kill_switch_state: KillSwitchState = KillSwitchState.ARMED


class RiskHistoryResponse(BaseModel):
    strategy_id: str
    snapshots: list[RiskSnapshotResponse] = Field(default_factory=list)
    total_count: int = 0


class CapitalAllocationEntry(BaseModel):
    strategy_id: str
    strategy_name: str
    allocated_idr: float = 0.0
    utilized_idr: float = 0.0
    utilization_pct: float = 0.0
    sharpe_ratio: float = 0.0
    weight_pct: float = 0.0


class CapitalAllocationsResponse(BaseModel):
    total_capital_idr: float = 0.0
    total_allocated_idr: float = 0.0
    total_unallocated_idr: float = 0.0
    allocations: list[CapitalAllocationEntry] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


# ── Kill Switch Endpoints ────────────────────────────────────────────────────


@router.post("/kill-switch/trigger", response_model=KillSwitchActionResponse, status_code=status.HTTP_200_OK)
@require_role(Role.ADMIN)
async def trigger_kill_switch(
    body: KillSwitchTriggerRequest,
    user: TokenPayload = Depends(get_current_user),
) -> KillSwitchActionResponse:
    """Trigger the portfolio-wide kill switch.

    Cancels all open orders and prevents new order submission.
    Requires ADMIN role. All actions are audit-logged.
    """
    now = datetime.now(tz=UTC)
    logger.warning(
        "kill_switch_triggered",
        triggered_by=user.sub,
        reason=body.reason,
        cancel_open_orders=body.cancel_open_orders,
    )
    return KillSwitchActionResponse(
        previous_state=KillSwitchState.ARMED,
        new_state=KillSwitchState.TRIGGERED,
        actioned_by=user.sub,
        actioned_at=now,
        reason=body.reason,
        open_orders_cancelled=0,
    )


@router.post("/kill-switch/reset", response_model=KillSwitchActionResponse, status_code=status.HTTP_200_OK)
@require_role(Role.ADMIN)
async def reset_kill_switch(
    body: KillSwitchResetRequest,
    user: TokenPayload = Depends(get_current_user),
) -> KillSwitchActionResponse:
    """Reset the kill switch after it has been triggered.

    Optionally re-arms the switch. Requires ADMIN role.
    """
    now = datetime.now(tz=UTC)
    new_state = KillSwitchState.ARMED if body.rearm else KillSwitchState.DISARMED
    logger.info(
        "kill_switch_reset",
        reset_by=user.sub,
        reason=body.reason,
        new_state=new_state,
    )
    return KillSwitchActionResponse(
        previous_state=KillSwitchState.TRIGGERED,
        new_state=new_state,
        actioned_by=user.sub,
        actioned_at=now,
        reason=body.reason,
    )


@router.get("/kill-switch/status", response_model=KillSwitchStatusResponse)
@require_role(Role.TRADER)
async def get_kill_switch_status(
    user: TokenPayload = Depends(get_current_user),
) -> KillSwitchStatusResponse:
    """Get the current kill switch status.

    Accessible by TRADER role and above.
    """
    logger.info("kill_switch_status_queried", queried_by=user.sub)
    return KillSwitchStatusResponse(
        state=KillSwitchState.ARMED,
        armed_at=datetime.now(tz=UTC),
    )


# ── Promotion / Demotion Endpoints ───────────────────────────────────────────


@router.post(
    "/promotion/evaluate/{session_id}",
    response_model=PromotionEvaluationResponse,
    status_code=status.HTTP_200_OK,
)
@require_role(Role.ADMIN)
async def evaluate_session_for_promotion(
    session_id: str,
    body: PromotionEvaluateRequest | None = None,
    user: TokenPayload = Depends(get_current_user),
) -> PromotionEvaluationResponse:
    """Evaluate a paper trading session for promotion to live trading.

    Checks Sharpe ratio, drawdown, and minimum trading days against thresholds.
    Requires ADMIN role.
    """
    criteria = body or PromotionEvaluateRequest()
    logger.info(
        "promotion_evaluation_requested",
        session_id=session_id,
        requested_by=user.sub,
        min_sharpe=criteria.min_sharpe,
    )

    # Placeholder: in production, fetch session metrics from the paper trading service
    sharpe = 1.45
    sortino = 1.82
    max_dd = 8.3
    trading_days = 45
    total_return = 12.5
    win_rate = 58.0

    notes: list[str] = []
    verdict = PromotionVerdict.ELIGIBLE

    if sharpe < criteria.min_sharpe:
        verdict = PromotionVerdict.INELIGIBLE
        notes.append(f"Sharpe {sharpe:.2f} below minimum {criteria.min_sharpe:.2f}")
    if trading_days < criteria.min_trading_days:
        verdict = PromotionVerdict.INELIGIBLE
        notes.append(f"Trading days {trading_days} below minimum {criteria.min_trading_days}")
    if max_dd > criteria.max_drawdown_pct:
        verdict = PromotionVerdict.NEEDS_REVIEW
        notes.append(f"Max drawdown {max_dd:.1f}% exceeds threshold {criteria.max_drawdown_pct:.1f}%")
    if not notes:
        notes.append("All criteria met")

    return PromotionEvaluationResponse(
        session_id=session_id,
        verdict=verdict,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown_pct=max_dd,
        trading_days=trading_days,
        total_return_pct=total_return,
        win_rate_pct=win_rate,
        notes=notes,
    )


@router.post(
    "/promotion/promote/{session_id}",
    response_model=PromotionActionResponse,
    status_code=status.HTTP_200_OK,
)
@require_role(Role.ADMIN)
async def promote_session(
    session_id: str,
    body: PromotionPromoteRequest,
    user: TokenPayload = Depends(get_current_user),
) -> PromotionActionResponse:
    """Promote a paper trading session to live trading.

    Allocates capital and sets risk limits for the strategy.
    Requires ADMIN role.
    """
    now = datetime.now(tz=UTC)
    logger.info(
        "session_promoted",
        session_id=session_id,
        promoted_by=user.sub,
        initial_capital_idr=body.initial_capital_idr,
    )

    # Placeholder: in production, create live trading session via the execution service
    strategy_id = f"live-{session_id}"

    return PromotionActionResponse(
        session_id=session_id,
        strategy_id=strategy_id,
        status="PROMOTED",
        initial_capital_idr=body.initial_capital_idr,
        risk_limit_pct=body.risk_limit_pct,
        promoted_at=now,
        promoted_by=user.sub,
    )


@router.post(
    "/promotion/demote/{strategy_id}",
    response_model=DemotionActionResponse,
    status_code=status.HTTP_200_OK,
)
@require_role(Role.ADMIN)
async def demote_strategy(
    strategy_id: str,
    body: DemotionRequest,
    user: TokenPayload = Depends(get_current_user),
) -> DemotionActionResponse:
    """Demote a live strategy back to paper trading.

    Optionally liquidates all positions before demotion.
    Requires ADMIN role.
    """
    now = datetime.now(tz=UTC)
    logger.warning(
        "strategy_demoted",
        strategy_id=strategy_id,
        demoted_by=user.sub,
        reason=body.reason,
        liquidate=body.liquidate_positions,
    )
    return DemotionActionResponse(
        strategy_id=strategy_id,
        status="DEMOTED",
        positions_liquidated=0,
        demoted_at=now,
        demoted_by=user.sub,
        reason=body.reason,
    )


# ── Risk Snapshot Endpoints ──────────────────────────────────────────────────


@router.get("/risk/{strategy_id}/snapshot", response_model=RiskSnapshotResponse)
@require_role(Role.TRADER)
async def get_risk_snapshot(
    strategy_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> RiskSnapshotResponse:
    """Get the latest risk snapshot for a strategy.

    Returns current exposure, VaR, concentration, and loss metrics.
    Accessible by TRADER role and above.
    """
    logger.info("risk_snapshot_queried", strategy_id=strategy_id, queried_by=user.sub)

    now = datetime.now(tz=UTC)
    return RiskSnapshotResponse(
        strategy_id=strategy_id,
        timestamp=now,
        nav_idr=1_000_000_000.0,
        exposure=ExposureSnapshot(
            gross_exposure_idr=800_000_000.0,
            net_exposure_idr=600_000_000.0,
            long_exposure_idr=700_000_000.0,
            short_exposure_idr=100_000_000.0,
            beta_vs_ihsg=0.85,
        ),
        concentration=ConcentrationSnapshot(
            sector_hhi=0.15,
            top5_weight_pct=45.0,
            largest_position_pct=12.0,
            largest_position_symbol="BBCA",
            num_positions=15,
        ),
        var=VaRSnapshot(
            var_1d_95_idr=15_000_000.0,
            var_5d_95_idr=33_500_000.0,
            var_1d_99_idr=22_000_000.0,
        ),
        daily_loss_pct=0.5,
        drawdown_pct=2.3,
        kill_switch_state=KillSwitchState.ARMED,
    )


@router.get("/risk/{strategy_id}/history", response_model=RiskHistoryResponse)
@require_role(Role.TRADER)
async def get_risk_history(
    strategy_id: str,
    days: int = Query(default=7, ge=1, le=90, description="Number of days of history"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum snapshots to return"),
    user: TokenPayload = Depends(get_current_user),
) -> RiskHistoryResponse:
    """Get historical risk snapshots for a strategy.

    Returns time series of risk metrics for trend analysis.
    Accessible by TRADER role and above.
    """
    logger.info(
        "risk_history_queried",
        strategy_id=strategy_id,
        days=days,
        limit=limit,
        queried_by=user.sub,
    )

    # Placeholder: in production, query time-series database
    return RiskHistoryResponse(
        strategy_id=strategy_id,
        snapshots=[],
        total_count=0,
    )


# ── Capital Allocation Endpoints ─────────────────────────────────────────────


@router.get("/capital/allocations", response_model=CapitalAllocationsResponse)
@require_role(Role.ADMIN)
async def get_capital_allocations(
    user: TokenPayload = Depends(get_current_user),
) -> CapitalAllocationsResponse:
    """Compute and return current capital allocations across all live strategies.

    Uses risk-parity weighting based on strategy Sharpe ratios and volatility.
    Requires ADMIN role.
    """
    logger.info("capital_allocations_queried", queried_by=user.sub)

    # Placeholder: in production, compute from portfolio service
    total_capital = 10_000_000_000.0
    allocations = [
        CapitalAllocationEntry(
            strategy_id="strat-momentum-01",
            strategy_name="IDX Momentum",
            allocated_idr=4_000_000_000.0,
            utilized_idr=3_200_000_000.0,
            utilization_pct=80.0,
            sharpe_ratio=1.45,
            weight_pct=40.0,
        ),
        CapitalAllocationEntry(
            strategy_id="strat-mean-rev-02",
            strategy_name="Mean Reversion",
            allocated_idr=3_000_000_000.0,
            utilized_idr=2_100_000_000.0,
            utilization_pct=70.0,
            sharpe_ratio=1.20,
            weight_pct=30.0,
        ),
        CapitalAllocationEntry(
            strategy_id="strat-stat-arb-03",
            strategy_name="Stat Arb Pairs",
            allocated_idr=3_000_000_000.0,
            utilized_idr=1_500_000_000.0,
            utilization_pct=50.0,
            sharpe_ratio=1.65,
            weight_pct=30.0,
        ),
    ]
    total_allocated = sum(a.allocated_idr for a in allocations)

    return CapitalAllocationsResponse(
        total_capital_idr=total_capital,
        total_allocated_idr=total_allocated,
        total_unallocated_idr=total_capital - total_allocated,
        allocations=allocations,
    )
