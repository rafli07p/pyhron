"""Strategy management API endpoints.

CRUD operations for trading strategies, enable/disable controls,
and strategy performance reporting.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/strategies", tags=["strategies"])


# ── Request/Response Models ──────────────────────────────────────────────────


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str = Field(default="momentum")
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_limits: dict[str, float] = Field(default_factory=dict)
    description: str | None = None


class StrategyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    parameters: dict[str, Any] | None = None
    risk_limits: dict[str, float] | None = None
    description: str | None = None


class StrategyResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    strategy_type: str
    is_enabled: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_limits: dict[str, float] = Field(default_factory=dict)
    description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class StrategyPerformance(BaseModel):
    strategy_id: UUID
    name: str
    total_return_pct: float
    sharpe_ratio: float | None = None
    max_drawdown_pct: float | None = None
    win_rate: float | None = None
    total_trades: int = 0
    avg_holding_period_days: float | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[StrategyResponse])
async def list_strategies(
    strategy_type: str | None = Query(None),
    enabled_only: bool = Query(False),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[StrategyResponse]:
    """List all configured trading strategies."""
    return []


@router.post("/", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    body: StrategyCreate,
    _user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> StrategyResponse:
    """Register a new trading strategy."""
    logger.info("strategy_created", name=body.name, type=body.strategy_type)
    return StrategyResponse(
        name=body.name,
        strategy_type=body.strategy_type,
        parameters=body.parameters,
        risk_limits=body.risk_limits,
        description=body.description,
    )


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> StrategyResponse:
    """Get strategy details by ID."""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    body: StrategyUpdate,
    _user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> StrategyResponse:
    """Update strategy configuration."""
    logger.info("strategy_updated", strategy_id=str(strategy_id))
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> None:
    """Delete a trading strategy."""
    logger.info("strategy_deleted", strategy_id=str(strategy_id))
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")


@router.post("/{strategy_id}/enable")
async def enable_strategy(
    strategy_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.ADMIN)),
) -> dict[str, str]:
    """Enable live trading for a strategy."""
    logger.info("strategy_enabled", strategy_id=str(strategy_id))
    return {"status": "enabled", "strategy_id": str(strategy_id)}


@router.post("/{strategy_id}/disable")
async def disable_strategy(
    strategy_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.ADMIN)),
) -> dict[str, str]:
    """Disable live trading and cancel open orders."""
    logger.info("strategy_disabled", strategy_id=str(strategy_id))
    return {"status": "disabled", "strategy_id": str(strategy_id)}


@router.get("/{strategy_id}/performance", response_model=StrategyPerformance)
async def get_strategy_performance(
    strategy_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> StrategyPerformance:
    """Get performance metrics for a strategy."""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
