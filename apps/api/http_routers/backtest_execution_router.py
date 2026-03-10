"""Backtest execution API endpoints.

Submit backtest jobs, poll for results, retrieve performance metrics,
and browse backtest history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/backtest", tags=["backtest"])


# ── Request/Response Models ──────────────────────────────────────────────────


class BacktestRequest(BaseModel):
    strategy_id: str
    symbols: list[str] = Field(..., min_length=1)
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal("1000000000")  # 1B IDR
    slippage_bps: float = Field(default=10.0, description="Slippage in basis points")
    commission_bps: float = Field(default=15.0, description="Commission in basis points")


class BacktestSubmission(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    status: str = "submitted"
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class BacktestResult(BaseModel):
    task_id: UUID
    status: str = Field(description="submitted, running, completed, failed")
    strategy_id: str
    symbols: list[str]
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_equity: Decimal | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class BacktestMetrics(BaseModel):
    task_id: UUID
    total_return_pct: float
    annualized_return_pct: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    max_drawdown_pct: float
    calmar_ratio: float | None = None
    win_rate: float
    profit_factor: float | None = None
    total_trades: int
    avg_trade_return_pct: float | None = None
    avg_holding_period_days: float | None = None


class BacktestHistoryEntry(BaseModel):
    task_id: UUID
    strategy_id: str
    status: str
    submitted_at: datetime
    total_return_pct: float | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/run", response_model=BacktestSubmission, status_code=202)
async def run_backtest(
    body: BacktestRequest,
    _user: TokenPayload = Depends(require_role(Role.ANALYST)),
) -> BacktestSubmission:
    """Submit an asynchronous backtest job. Returns task_id for polling."""
    logger.info(
        "backtest_submitted",
        strategy_id=body.strategy_id,
        symbols=body.symbols,
        start=body.start_date.isoformat(),
        end=body.end_date.isoformat(),
    )
    return BacktestSubmission()


@router.get("/{task_id}", response_model=BacktestResult)
async def get_backtest_result(
    task_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.ANALYST)),
) -> BacktestResult:
    """Get backtest result and status by task_id."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Backtest {task_id} not found",
    )


@router.get("/{task_id}/metrics", response_model=BacktestMetrics)
async def get_backtest_metrics(
    task_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.ANALYST)),
) -> BacktestMetrics:
    """Get detailed performance metrics for a completed backtest."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Backtest {task_id} not found",
    )


@router.get("/history", response_model=list[BacktestHistoryEntry])
async def get_backtest_history(
    strategy_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    _user: TokenPayload = Depends(require_role(Role.ANALYST)),
) -> list[BacktestHistoryEntry]:
    """Browse backtest submission history."""
    return []
