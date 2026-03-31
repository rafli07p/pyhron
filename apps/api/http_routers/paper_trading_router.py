"""Paper trading API endpoints.

Session lifecycle management, NAV history, P&L attribution,
simulation execution, and reconciliation reporting.
"""




from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from data_platform.database_models.paper_trading_session import (
    PaperNavSnapshot,
    PaperPnlAttribution,
    PaperTradingSession,
)
from services.paper_trading.session_manager import PaperTradingSessionManager
from shared.async_database_session import get_session
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/paper-trading", tags=["paper-trading"])

_session_manager = PaperTradingSessionManager()


# Request/Response Models
class CreatePaperSessionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    strategy_id: UUID
    initial_capital_idr: Decimal = Field(..., gt=0)
    mode: str = Field(default="LIVE_HOURS", pattern="^(LIVE_HOURS|SIMULATION)$")


class PaperSessionResponse(BaseModel):
    id: UUID
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


# Helpers
def _session_to_response(s: PaperTradingSession) -> PaperSessionResponse:
    return PaperSessionResponse(
        id=s.id,
        name=s.name,
        strategy_id=s.strategy_id,
        status=s.status,
        mode=s.mode,
        initial_capital_idr=s.initial_capital_idr,
        current_nav_idr=s.current_nav_idr,
        peak_nav_idr=s.peak_nav_idr,
        max_drawdown_pct=float(s.max_drawdown_pct),
        total_trades=s.total_trades,
        winning_trades=s.winning_trades,
        realized_pnl_idr=s.realized_pnl_idr,
        total_commission_idr=s.total_commission_idr,
        cash_idr=s.cash_idr,
        unsettled_cash_idr=s.unsettled_cash_idr,
        started_at=s.started_at,
        stopped_at=s.stopped_at,
        created_at=s.created_at,
    )


async def _get_session_or_404(session_id: UUID) -> PaperTradingSession:
    async with get_session() as db:
        result = await db.execute(
            select(PaperTradingSession).where(PaperTradingSession.id == session_id),
        )
        session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper trading session not found")
    return session


# Endpoints
@router.post("/sessions", response_model=PaperSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_paper_session(
    request: CreatePaperSessionRequest,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> PaperSessionResponse:
    """Create a new paper trading session."""
    try:
        async with get_session() as db:
            session = await _session_manager.create_session(
                name=request.name,
                strategy_id=str(request.strategy_id),
                initial_capital_idr=request.initial_capital_idr,
                mode=request.mode,
                created_by=user.sub,
                db_session=db,
            )
            return _session_to_response(session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/sessions/{session_id}/start")
async def start_paper_session(
    session_id: UUID,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> dict[str, str]:
    """Start a paper trading session."""
    try:
        async with get_session() as db:
            await _session_manager.start_session(str(session_id), db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"status": "started", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/pause")
async def pause_paper_session(
    session_id: UUID,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> dict[str, str]:
    """Pause a running paper trading session."""
    try:
        async with get_session() as db:
            await _session_manager.pause_session(str(session_id), db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"status": "paused", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/resume")
async def resume_paper_session(
    session_id: UUID,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> dict[str, str]:
    """Resume a paused paper trading session."""
    try:
        async with get_session() as db:
            await _session_manager.resume_session(str(session_id), db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"status": "resumed", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/stop", response_model=PaperSessionSummaryResponse)
async def stop_paper_session(
    session_id: UUID,
    close_positions: bool = True,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> PaperSessionSummaryResponse:
    """Stop a paper trading session and return summary."""
    try:
        async with get_session() as db:
            summary = await _session_manager.stop_session(
                str(session_id),
                db,
                close_positions=close_positions,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return PaperSessionSummaryResponse(
        session_id=summary.session_id,
        name=summary.name,
        initial_capital_idr=summary.initial_capital_idr,
        final_nav_idr=summary.final_nav_idr,
        total_return_pct=summary.total_return_pct,
        max_drawdown_pct=summary.max_drawdown_pct,
        sharpe_ratio=summary.sharpe_ratio,
        sortino_ratio=summary.sortino_ratio,
        calmar_ratio=summary.calmar_ratio,
        total_trades=summary.total_trades,
        winning_trades=summary.winning_trades,
        win_rate_pct=summary.win_rate_pct,
        total_commission_idr=summary.total_commission_idr,
        net_return_after_costs_pct=summary.net_return_after_costs_pct,
        duration_days=summary.duration_days,
        started_at=summary.started_at,
        stopped_at=summary.stopped_at,
    )


@router.get("/sessions/{session_id}/nav", response_model=list[PaperNavSnapshotResponse])
async def get_nav_history(
    session_id: UUID,
    lookback_hours: int = Query(default=8, ge=1, le=720),
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> list[PaperNavSnapshotResponse]:
    """Get NAV snapshot history."""
    await _get_session_or_404(session_id)
    cutoff = datetime.now(tz=UTC) - timedelta(hours=lookback_hours)

    async with get_session() as db:
        result = await db.execute(
            select(PaperNavSnapshot)
            .where(
                PaperNavSnapshot.session_id == session_id,
                PaperNavSnapshot.timestamp >= cutoff,
            )
            .order_by(PaperNavSnapshot.timestamp.asc()),
        )
        snapshots = result.scalars().all()

    return [
        PaperNavSnapshotResponse(
            timestamp=s.timestamp,
            nav_idr=s.nav_idr,
            cash_idr=s.cash_idr,
            gross_exposure_idr=s.gross_exposure_idr,
            drawdown_pct=float(s.drawdown_pct),
            daily_pnl_idr=s.daily_pnl_idr,
            daily_return_pct=float(s.daily_return_pct),
        )
        for s in snapshots
    ]


@router.get("/sessions/{session_id}/attribution", response_model=AttributionReportResponse)
async def get_pnl_attribution(
    session_id: UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> AttributionReportResponse:
    """Get P&L attribution report for date range."""
    await _get_session_or_404(session_id)

    async with get_session() as db:
        result = await db.execute(
            select(PaperPnlAttribution).where(
                PaperPnlAttribution.session_id == session_id,
                PaperPnlAttribution.date >= date_from,
                PaperPnlAttribution.date <= date_to,
            ),
        )
        attributions = result.scalars().all()

    total_realized = Decimal("0")
    total_unrealized = Decimal("0")
    total_commission = Decimal("0")
    total_turnover = Decimal("0")
    total_trades = 0
    by_symbol: dict[str, Any] = {}
    by_signal_source: dict[str, Any] = {}

    for a in attributions:
        total_realized += a.realized_pnl_idr
        total_unrealized += a.unrealized_pnl_idr
        total_commission += a.commission_idr
        total_turnover += a.turnover_idr
        total_trades += a.trades_count

        # Aggregate by symbol
        sym = a.symbol
        if sym not in by_symbol:
            by_symbol[sym] = {"realized_pnl_idr": Decimal("0"), "unrealized_pnl_idr": Decimal("0"), "trades": 0}
        by_symbol[sym]["realized_pnl_idr"] += a.realized_pnl_idr
        by_symbol[sym]["unrealized_pnl_idr"] += a.unrealized_pnl_idr
        by_symbol[sym]["trades"] += a.trades_count

        # Aggregate by signal source
        src = a.signal_source or "unknown"
        if src not in by_signal_source:
            by_signal_source[src] = {"realized_pnl_idr": Decimal("0"), "trades": 0}
        by_signal_source[src]["realized_pnl_idr"] += a.realized_pnl_idr
        by_signal_source[src]["trades"] += a.trades_count

    # Convert Decimals for JSON serialization
    for v in by_symbol.values():
        v["realized_pnl_idr"] = str(v["realized_pnl_idr"])
        v["unrealized_pnl_idr"] = str(v["unrealized_pnl_idr"])
    for v in by_signal_source.values():
        v["realized_pnl_idr"] = str(v["realized_pnl_idr"])

    return AttributionReportResponse(
        session_id=str(session_id),
        date_from=date_from,
        date_to=date_to,
        total_realized_pnl_idr=total_realized,
        total_unrealized_pnl_idr=total_unrealized,
        total_commission_idr=total_commission,
        total_turnover_idr=total_turnover,
        total_trades=total_trades,
        by_symbol=by_symbol,
        by_signal_source=by_signal_source,
    )


@router.post("/sessions/{session_id}/simulate", response_model=PaperSessionSummaryResponse)
async def run_simulation(
    session_id: UUID,
    request: SimulationRequest,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> PaperSessionSummaryResponse:
    """Run a simulation for the given date range.

    Starts the session if it's in INITIALIZING state, runs
    the simulation engine, then returns the summary.
    """
    session = await _get_session_or_404(session_id)

    # Auto-start if in INITIALIZING state
    if session.status == "INITIALIZING":
        async with get_session() as db:
            await _session_manager.start_session(str(session_id), db)

    try:
        from services.paper_trading.simulation_engine import PaperSimulationEngine

        engine = PaperSimulationEngine()
        async with get_session() as db:
            # Reload session inside this db context
            result = await db.execute(select(PaperTradingSession).where(PaperTradingSession.id == session_id))
            db_session_obj = result.scalar_one()
            await engine.run(
                session=db_session_obj,
                date_from=request.date_from,
                date_to=request.date_to,
                slippage_bps=request.slippage_bps,
                db_session=db,
            )
            summary = await _session_manager.stop_session(str(session_id), db)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return PaperSessionSummaryResponse(
        session_id=summary.session_id,
        name=summary.name,
        initial_capital_idr=summary.initial_capital_idr,
        final_nav_idr=summary.final_nav_idr,
        total_return_pct=summary.total_return_pct,
        max_drawdown_pct=summary.max_drawdown_pct,
        sharpe_ratio=summary.sharpe_ratio,
        sortino_ratio=summary.sortino_ratio,
        calmar_ratio=summary.calmar_ratio,
        total_trades=summary.total_trades,
        winning_trades=summary.winning_trades,
        win_rate_pct=summary.win_rate_pct,
        total_commission_idr=summary.total_commission_idr,
        net_return_after_costs_pct=summary.net_return_after_costs_pct,
        duration_days=summary.duration_days,
        started_at=summary.started_at,
        stopped_at=summary.stopped_at,
    )


@router.get("/sessions/{session_id}/reconciliation", response_model=ReconciliationReportResponse)
async def get_reconciliation_report(
    session_id: UUID,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> ReconciliationReportResponse:
    """Get latest reconciliation report by comparing session positions."""
    session = await _get_session_or_404(session_id)

    from data_platform.database_models.order_lifecycle_record import (
        OrderLifecycleRecord,
        OrderStatusEnum,
    )
    from data_platform.database_models.strategy_position_snapshot import StrategyPositionSnapshot

    async with get_session() as db:
        # Count positions for this strategy
        pos_result = await db.execute(
            select(func.count())
            .select_from(StrategyPositionSnapshot)
            .where(
                StrategyPositionSnapshot.strategy_id == str(session.strategy_id),
                StrategyPositionSnapshot.quantity > 0,
            ),
        )
        positions_checked = pos_result.scalar() or 0

        # Count open/active orders
        orders_result = await db.execute(
            select(func.count())
            .select_from(OrderLifecycleRecord)
            .where(
                OrderLifecycleRecord.strategy_id == str(session.strategy_id),
                OrderLifecycleRecord.status.in_(
                    [
                        OrderStatusEnum.SUBMITTED,
                        OrderStatusEnum.ACKNOWLEDGED,
                        OrderStatusEnum.PARTIAL_FILL,
                    ]
                ),
            ),
        )
        orders_checked = orders_result.scalar() or 0

    return ReconciliationReportResponse(
        session_id=str(session_id),
        reconciled_at=datetime.now(tz=UTC),
        positions_checked=positions_checked,
        orders_checked=orders_checked,
    )


# Consumer Health Check
# Singleton reference set by the consumer process when it starts.
# When the API runs in-process with the consumer (e.g. dev/test), this
# allows the health endpoint to report consumer status.
_consumer_instance: Any = None


def register_consumer(consumer: Any) -> None:
    """Register a running StrategySignalKafkaConsumer for health reporting."""
    global _consumer_instance
    _consumer_instance = consumer


@router.get("/consumer/health", tags=["ops"])
async def consumer_health() -> dict[str, Any]:
    """Health check for the strategy signal Kafka consumer."""
    if _consumer_instance is None:
        return {
            "status": "not_registered",
            "message": "No consumer instance registered with the API process",
        }

    health = _consumer_instance.health()
    return {
        "status": health.status,
        "running": health.running,
        "started_at": health.started_at.isoformat() if health.started_at else None,
        "last_message_at": health.last_message_at.isoformat() if health.last_message_at else None,
        "messages_processed": health.messages_processed,
        "batches_flushed": health.batches_flushed,
        "errors": health.errors,
        "topics": health.topics,
        "consumer_group": health.consumer_group,
    }
