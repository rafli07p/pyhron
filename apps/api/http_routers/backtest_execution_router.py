"""Backtest execution API endpoints.

Submit backtest jobs, poll for results, retrieve performance metrics,
and browse backtest history.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/backtest", tags=["backtest"])

# In-memory task status tracking (for submitted/running jobs)
_task_status: dict[str, dict[str, Any]] = {}


# Request/Response Models
class BacktestRequest(BaseModel):
    strategy_type: str = Field(default="momentum", description="Strategy name")
    symbols: list[str] = Field(..., min_length=1)
    start_date: date
    end_date: date
    initial_capital: Decimal = Decimal("1000000000")  # 1B IDR
    slippage_bps: float = Field(default=5.0, description="Slippage in basis points")
    strategy_params: dict[str, Any] | None = Field(default=None, description="Strategy-specific parameters")


class BacktestSubmission(BaseModel):
    task_id: UUID
    status: str = "submitted"
    submitted_at: datetime


class BacktestResultResponse(BaseModel):
    task_id: UUID
    status: str
    strategy_name: str | None = None
    symbols: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    initial_capital: Decimal | None = None
    final_capital: Decimal | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class BacktestMetrics(BaseModel):
    task_id: UUID
    total_return_pct: float
    cagr_pct: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None
    max_drawdown_pct: float
    max_drawdown_duration_days: int | None = None
    win_rate_pct: float
    profit_factor: float | None = None
    omega_ratio: float | None = None
    total_trades: int
    cost_drag_annualized_pct: float | None = None


class BacktestHistoryEntry(BaseModel):
    task_id: UUID
    strategy_name: str | None = None
    status: str
    submitted_at: datetime
    total_return_pct: float | None = None
    sharpe_ratio: float | None = None


# Background Task
async def _run_backtest_task(
    task_id: str,
    body: BacktestRequest,
) -> None:
    """Execute a backtest in the background and persist results."""
    from services.backtesting.backtest_orchestrator import run_backtest

    _task_status[task_id] = {"status": "running", "started_at": datetime.now(UTC)}

    try:
        result = await run_backtest(
            strategy_type=body.strategy_type,
            symbols=body.symbols,
            start_date=body.start_date,
            end_date=body.end_date,
            initial_capital_idr=body.initial_capital,
            strategy_params=body.strategy_params,
            slippage_bps=body.slippage_bps,
            db_session=None,  # Use synthetic data for API backtests by default
        )

        _task_status[task_id] = {
            "status": "completed",
            "completed_at": datetime.now(UTC),
            "result": {
                "strategy_name": result.strategy_name,
                "total_return_pct": result.total_return_pct,
                "cagr_pct": result.cagr_pct,
                "sharpe_ratio": result.sharpe_ratio,
                "sortino_ratio": result.sortino_ratio,
                "calmar_ratio": result.calmar_ratio,
                "omega_ratio": result.omega_ratio,
                "max_drawdown_pct": result.max_drawdown_pct,
                "max_drawdown_duration_days": result.max_drawdown_duration_days,
                "total_trades": result.total_trades,
                "win_rate_pct": result.win_rate_pct,
                "profit_factor": result.profit_factor,
                "cost_drag_annualized_pct": result.cost_drag_annualized_pct,
                "initial_capital": str(result.initial_capital_idr),
                "final_capital": str(result.initial_capital_idr * Decimal(str(1 + result.total_return_pct / 100))),
            },
            "symbols": body.symbols,
            "start_date": body.start_date,
            "end_date": body.end_date,
        }

        logger.info(
            "backtest_task_completed",
            task_id=task_id,
            total_return_pct=result.total_return_pct,
        )

    except Exception as exc:
        _task_status[task_id] = {
            "status": "failed",
            "error_message": str(exc),
            "completed_at": datetime.now(UTC),
        }
        logger.exception("backtest_task_failed", task_id=task_id)


# Endpoints
@router.post("/run", response_model=BacktestSubmission, status_code=202)
async def submit_backtest(
    body: BacktestRequest,
    background_tasks: BackgroundTasks,
    _user: TokenPayload = Depends(require_role(Role.ANALYST)),
) -> BacktestSubmission:
    """Submit an asynchronous backtest job. Returns task_id for polling."""
    task_id = str(uuid4())
    submitted_at = datetime.now(UTC)

    _task_status[task_id] = {"status": "submitted", "submitted_at": submitted_at}
    background_tasks.add_task(_run_backtest_task, task_id, body)

    logger.info(
        "backtest_submitted",
        task_id=task_id,
        strategy_type=body.strategy_type,
        symbols=body.symbols,
    )
    return BacktestSubmission(
        task_id=UUID(task_id),
        status="submitted",
        submitted_at=submitted_at,
    )


@router.get("/{task_id}", response_model=BacktestResultResponse)
async def get_backtest_result(
    task_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.ANALYST)),
) -> BacktestResultResponse:
    """Get backtest result and status by task_id."""
    task = _task_status.get(str(task_id))
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest {task_id} not found",
        )

    result_data = task.get("result", {})
    return BacktestResultResponse(
        task_id=task_id,
        status=task["status"],
        strategy_name=result_data.get("strategy_name"),
        symbols=task.get("symbols"),
        start_date=task.get("start_date"),
        end_date=task.get("end_date"),
        initial_capital=Decimal(result_data["initial_capital"]) if "initial_capital" in result_data else None,
        final_capital=Decimal(result_data["final_capital"]) if "final_capital" in result_data else None,
        completed_at=task.get("completed_at"),
        error_message=task.get("error_message"),
    )


@router.get("/{task_id}/metrics", response_model=BacktestMetrics)
async def get_backtest_metrics(
    task_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.ANALYST)),
) -> BacktestMetrics:
    """Get detailed performance metrics for a completed backtest."""
    task = _task_status.get(str(task_id))
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest {task_id} not found",
        )

    if task["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Backtest {task_id} is {task['status']}, not completed",
        )

    r = task["result"]
    return BacktestMetrics(
        task_id=task_id,
        total_return_pct=r["total_return_pct"],
        cagr_pct=r["cagr_pct"],
        sharpe_ratio=r["sharpe_ratio"],
        sortino_ratio=r["sortino_ratio"],
        calmar_ratio=r["calmar_ratio"],
        max_drawdown_pct=r["max_drawdown_pct"],
        max_drawdown_duration_days=r["max_drawdown_duration_days"],
        win_rate_pct=r["win_rate_pct"],
        profit_factor=r["profit_factor"],
        omega_ratio=r["omega_ratio"],
        total_trades=r["total_trades"],
        cost_drag_annualized_pct=r["cost_drag_annualized_pct"],
    )


@router.get("/history", response_model=list[BacktestHistoryEntry])
async def get_backtest_history(
    strategy_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    _user: TokenPayload = Depends(require_role(Role.ANALYST)),
) -> list[BacktestHistoryEntry]:
    """Browse backtest submission history (from in-memory store)."""
    entries = []
    for tid, task in list(_task_status.items())[-limit:]:
        result_data = task.get("result", {})
        if status_filter and task["status"] != status_filter:
            continue
        entries.append(
            BacktestHistoryEntry(
                task_id=UUID(tid),
                strategy_name=result_data.get("strategy_name"),
                status=task["status"],
                submitted_at=task.get("submitted_at", datetime.now(UTC)),
                total_return_pct=result_data.get("total_return_pct"),
                sharpe_ratio=result_data.get("sharpe_ratio"),
            )
        )
    return entries
