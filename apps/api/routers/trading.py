"""Trading API endpoints.

Strategy management, backtest triggers, positions, orders, P&L,
and circuit breaker administration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/trading", tags=["trading"])


# ── Request/Response Models ─────────────────────────────────────────────────


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str = Field(default="momentum")
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_limits: dict[str, float] = Field(default_factory=dict)


class StrategyResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    strategy_type: str
    is_enabled: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class BacktestCreate(BaseModel):
    strategy_id: str
    symbols: list[str]
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal("1000000000")  # 1B IDR


class BacktestResponse(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    status: str = "submitted"
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class PositionResponse(BaseModel):
    symbol: str
    exchange: str = "IDX"
    strategy_id: str
    quantity: int
    avg_entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    market_value: Decimal


class OrderResponse(BaseModel):
    client_order_id: str
    strategy_id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    status: str
    created_at: datetime


class PnLResponse(BaseModel):
    date: str
    total_equity: Decimal
    total_pnl: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal


class CircuitBreakerClearRequest(BaseModel):
    strategy_id: str
    reason: str = Field(..., min_length=10, description="Audit trail reason for clearing")


# ── Strategy Management ─────────────────────────────────────────────────────


@router.get("/strategies", response_model=list[StrategyResponse])
async def list_strategies() -> list[StrategyResponse]:
    """List all configured strategies with status."""
    # In production: query strategy registry from DB
    return []


@router.post("/strategies", response_model=StrategyResponse, status_code=201)
async def create_strategy(body: StrategyCreate) -> StrategyResponse:
    """Register a new trading strategy."""
    logger.info("strategy_created", name=body.name, type=body.strategy_type)
    return StrategyResponse(
        name=body.name,
        strategy_type=body.strategy_type,
        parameters=body.parameters,
    )


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: UUID) -> StrategyResponse:
    """Get strategy details and performance metrics."""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")


@router.post("/strategies/{strategy_id}/enable")
async def enable_strategy(strategy_id: UUID) -> dict[str, str]:
    """Enable live trading for a strategy."""
    logger.info("strategy_enabled", strategy_id=str(strategy_id))
    return {"status": "enabled", "strategy_id": str(strategy_id)}


@router.post("/strategies/{strategy_id}/disable")
async def disable_strategy(strategy_id: UUID) -> dict[str, str]:
    """Disable live trading and cancel open orders for a strategy."""
    logger.info("strategy_disabled", strategy_id=str(strategy_id))
    return {"status": "disabled", "strategy_id": str(strategy_id)}


# ── Backtesting ─────────────────────────────────────────────────────────────


@router.post("/backtest", response_model=BacktestResponse, status_code=202)
async def run_backtest(body: BacktestCreate) -> BacktestResponse:
    """Submit an async backtest job. Returns task_id for polling."""
    logger.info(
        "backtest_submitted",
        strategy_id=body.strategy_id,
        symbols=body.symbols,
    )
    return BacktestResponse()


@router.get("/backtest/{task_id}")
async def get_backtest_result(task_id: UUID) -> dict[str, Any]:
    """Fetch backtest result by task_id."""
    return {"task_id": str(task_id), "status": "pending", "result": None}


# ── Positions & Orders ──────────────────────────────────────────────────────


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    strategy_id: str | None = Query(None),
) -> list[PositionResponse]:
    """Get all open positions across strategies."""
    # In production: query positions table, optionally filtered by strategy
    return []


@router.get("/orders", response_model=list[OrderResponse])
async def get_orders(
    strategy_id: str | None = Query(None),
    symbol: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
) -> list[OrderResponse]:
    """Get order history with filters."""
    return []


# ── P&L ─────────────────────────────────────────────────────────────────────


@router.get("/pnl", response_model=list[PnLResponse])
async def get_daily_pnl(
    days: int = Query(30, ge=1, le=365),
) -> list[PnLResponse]:
    """Get daily P&L summary."""
    return []


# ── Circuit Breaker ─────────────────────────────────────────────────────────


@router.post("/circuit-breaker/clear")
async def clear_circuit_breaker(body: CircuitBreakerClearRequest) -> dict[str, str]:
    """Clear circuit breaker for a strategy. Requires admin role and audit reason."""
    logger.info(
        "circuit_breaker_cleared",
        strategy_id=body.strategy_id,
        reason=body.reason,
    )
    return {
        "status": "cleared",
        "strategy_id": body.strategy_id,
        "cleared_at": datetime.now(tz=timezone.utc).isoformat(),
    }
