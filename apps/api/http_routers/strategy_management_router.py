"""Strategy management API endpoints.

CRUD operations for trading strategies, enable/disable controls,
and strategy performance reporting.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from data_platform.database_models.pyhron_backtest_run import BacktestStatus, PyhronBacktestRun
from data_platform.database_models.pyhron_strategy import PyhronStrategy
from shared.async_database_session import get_session
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/strategies", tags=["strategies"])


# Request/Response Models
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
    id: UUID
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


# Helpers
def _to_response(s: PyhronStrategy) -> StrategyResponse:
    return StrategyResponse(
        id=s.id,
        name=s.name,
        strategy_type=s.strategy_type,
        is_enabled=s.is_active,
        parameters=s.parameters or {},
        risk_limits=s.risk_config or {},
        description=None,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


# Endpoints
@router.get("/", response_model=list[StrategyResponse])
async def list_strategies(
    strategy_type: str | None = Query(None),
    enabled_only: bool = Query(False),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[StrategyResponse]:
    """List all configured trading strategies."""
    async with get_session() as session:
        stmt = select(PyhronStrategy).order_by(PyhronStrategy.created_at.desc())
        if strategy_type:
            stmt = stmt.where(PyhronStrategy.strategy_type == strategy_type)
        if enabled_only:
            stmt = stmt.where(PyhronStrategy.is_active.is_(True))
        result = await session.execute(stmt)
        strategies = result.scalars().all()
    return [_to_response(s) for s in strategies]


@router.post("/", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    body: StrategyCreate,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> StrategyResponse:
    """Register a new trading strategy."""
    async with get_session() as session:
        strategy = PyhronStrategy(
            user_id=UUID(user.sub),
            name=body.name,
            strategy_type=body.strategy_type,
            parameters=body.parameters or {},
            risk_config=body.risk_limits or {},
            is_active=False,
            is_live=False,
        )
        session.add(strategy)
        await session.flush()
        await session.refresh(strategy)

        logger.info(
            "strategy_created",
            strategy_id=str(strategy.id),
            name=body.name,
            type=body.strategy_type,
            user=user.sub,
        )
        return _to_response(strategy)


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> StrategyResponse:
    """Get strategy details by ID."""
    async with get_session() as session:
        result = await session.execute(
            select(PyhronStrategy).where(PyhronStrategy.id == strategy_id),
        )
        strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return _to_response(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    body: StrategyUpdate,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> StrategyResponse:
    """Update strategy configuration."""
    async with get_session() as session:
        result = await session.execute(
            select(PyhronStrategy).where(PyhronStrategy.id == strategy_id),
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

        if body.name is not None:
            strategy.name = body.name
        if body.parameters is not None:
            strategy.parameters = body.parameters
        if body.risk_limits is not None:
            strategy.risk_config = body.risk_limits
        strategy.updated_at = datetime.now(tz=UTC)

        await session.flush()
        await session.refresh(strategy)

        logger.info("strategy_updated", strategy_id=str(strategy_id), user=user.sub)
        return _to_response(strategy)


@router.delete("/{strategy_id}", status_code=204, response_model=None)
async def delete_strategy(
    strategy_id: UUID,
    user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> None:
    """Delete a trading strategy."""
    async with get_session() as session:
        result = await session.execute(
            select(PyhronStrategy).where(PyhronStrategy.id == strategy_id),
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

        await session.delete(strategy)
        logger.info("strategy_deleted", strategy_id=str(strategy_id), user=user.sub)


@router.post("/{strategy_id}/enable")
async def enable_strategy(
    strategy_id: UUID,
    user: TokenPayload = Depends(require_role(Role.ADMIN)),
) -> dict[str, str]:
    """Enable live trading for a strategy."""
    async with get_session() as session:
        result = await session.execute(
            select(PyhronStrategy).where(PyhronStrategy.id == strategy_id),
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

        strategy.is_active = True
        strategy.updated_at = datetime.now(tz=UTC)
        await session.flush()

    logger.info("strategy_enabled", strategy_id=str(strategy_id), user=user.sub)
    return {"status": "enabled", "strategy_id": str(strategy_id)}


@router.post("/{strategy_id}/disable")
async def disable_strategy(
    strategy_id: UUID,
    user: TokenPayload = Depends(require_role(Role.ADMIN)),
) -> dict[str, str]:
    """Disable live trading and cancel open orders."""
    async with get_session() as session:
        result = await session.execute(
            select(PyhronStrategy).where(PyhronStrategy.id == strategy_id),
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

        strategy.is_active = False
        strategy.is_live = False
        strategy.updated_at = datetime.now(tz=UTC)
        await session.flush()

    logger.info("strategy_disabled", strategy_id=str(strategy_id), user=user.sub)
    return {"status": "disabled", "strategy_id": str(strategy_id)}


@router.get("/{strategy_id}/performance", response_model=StrategyPerformance)
async def get_strategy_performance(
    strategy_id: UUID,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> StrategyPerformance:
    """Get performance metrics for a strategy from latest completed backtest."""
    async with get_session() as session:
        # Get strategy name
        strat_result = await session.execute(
            select(PyhronStrategy).where(PyhronStrategy.id == strategy_id),
        )
        strategy = strat_result.scalar_one_or_none()
        if not strategy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

        # Get latest completed backtest
        bt_result = await session.execute(
            select(PyhronBacktestRun)
            .where(
                PyhronBacktestRun.strategy_id == strategy_id,
                PyhronBacktestRun.status == BacktestStatus.COMPLETED,
            )
            .order_by(PyhronBacktestRun.completed_at.desc())
            .limit(1),
        )
        backtest = bt_result.scalar_one_or_none()

    if not backtest:
        return StrategyPerformance(
            strategy_id=strategy_id,
            name=strategy.name,
            total_return_pct=0.0,
        )

    return StrategyPerformance(
        strategy_id=strategy_id,
        name=strategy.name,
        total_return_pct=float(backtest.total_return_pct or 0),
        sharpe_ratio=float(backtest.sharpe_ratio) if backtest.sharpe_ratio else None,
        max_drawdown_pct=float(backtest.max_drawdown_pct) if backtest.max_drawdown_pct else None,
        win_rate=float(backtest.win_rate_pct) if backtest.win_rate_pct else None,
        total_trades=backtest.total_trades or 0,
        period_start=backtest.started_at,
        period_end=backtest.completed_at,
    )
