"""Live trading position API endpoints.

Open positions, order management, P&L tracking,
and circuit breaker administration.
"""

import contextlib
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from data_platform.database_models.pyhron_order_lifecycle_record import (
    OrderStatusEnum,
    PyhronOrderLifecycleRecord,
)
from data_platform.database_models.pyhron_strategy_position_snapshot import (
    PyhronStrategyPositionSnapshot,
)
from services.order_management_system.order_submission_handler import (
    OrderSubmissionHandler,
)
from services.pre_trade_risk_engine.circuit_breaker_state_manager import (
    CircuitBreakerStateManager,
)
from shared.async_database_session import get_session
from shared.platform_exception_hierarchy import (
    CircuitBreakerOpenError,
    DuplicateOrderError,
    PyhronValidationError,
)
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/trading", tags=["trading"])

# Injected at app startup via set_order_handler()
_order_handler: OrderSubmissionHandler | None = None


def set_order_handler(handler: OrderSubmissionHandler) -> None:
    """Inject the OrderSubmissionHandler at application startup."""
    global _order_handler
    _order_handler = handler


def _get_order_handler() -> OrderSubmissionHandler:
    if _order_handler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order management service not available",
        )
    return _order_handler


# Response Models
class PositionResponse(BaseModel):
    symbol: str
    exchange: str = "IDX"
    strategy_id: str
    quantity: int
    avg_entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    market_value: Decimal
    weight_pct: float = Field(description="Portfolio weight percentage")


class OrderResponse(BaseModel):
    client_order_id: str
    strategy_id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    filled_quantity: int = 0
    limit_price: Decimal | None = None
    status: str
    created_at: datetime


class PnLResponse(BaseModel):
    date: str
    total_equity: Decimal
    total_pnl: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    daily_return_pct: float = 0.0


class CircuitBreakerStatus(BaseModel):
    strategy_id: str
    is_tripped: bool
    tripped_at: datetime | None = None
    reason: str | None = None


class CircuitBreakerClearRequest(BaseModel):
    strategy_id: str
    reason: str = Field(..., min_length=10, description="Audit trail reason for clearing")


class OrderSubmitRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="IDX instrument symbol")
    side: str = Field(..., pattern=r"^(BUY|SELL)$", description="BUY or SELL")
    order_type: str = Field(default="LIMIT", pattern=r"^(MARKET|LIMIT)$", description="MARKET or LIMIT")
    quantity_lots: int = Field(..., gt=0, description="Quantity in IDX lots (1 lot = 100 shares)")
    limit_price: Decimal | None = Field(default=None, ge=0, description="Limit price in IDR")
    strategy_id: str | None = Field(default=None, max_length=100, description="Strategy identifier")


# Order Submission
@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def submit_order(
    body: OrderSubmitRequest,
    user: TokenPayload = Depends(require_role(Role.ADMIN, Role.TRADER)),
    handler: OrderSubmissionHandler = Depends(_get_order_handler),
) -> OrderResponse:
    """Submit a new order to the IDX exchange.

    Requires JWT authentication with ADMIN or TRADER role.
    """
    user_id = user.sub
    idempotency_key = f"{user_id}:{body.symbol}:{body.side}:{body.quantity_lots}:{int(time.time() // 60)}"

    try:
        record = await handler.submit_order(
            user_id=user_id,
            strategy_id=body.strategy_id,
            symbol=body.symbol,
            side=body.side,
            order_type=body.order_type,
            quantity_lots=body.quantity_lots,
            limit_price=body.limit_price,
            idempotency_key=idempotency_key,
        )
    except CircuitBreakerOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Circuit breaker is OPEN: {exc}",
        ) from exc
    except DuplicateOrderError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PyhronValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "errors": exc.errors},
        ) from exc

    return OrderResponse(
        client_order_id=record.client_order_id,
        strategy_id=record.strategy_id,
        symbol=record.symbol,
        side=record.side.value if hasattr(record.side, "value") else record.side,
        order_type=record.order_type.value if hasattr(record.order_type, "value") else record.order_type,
        quantity=record.quantity,
        filled_quantity=record.filled_quantity or 0,
        limit_price=record.limit_price,
        status=record.status.value if hasattr(record.status, "value") else record.status,
        created_at=record.created_at,
    )


# Positions
@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    strategy_id: str | None = Query(None),
    symbol: str | None = Query(None),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[PositionResponse]:
    """Get all open positions, optionally filtered by strategy or symbol."""
    async with get_session() as session:
        stmt = select(PyhronStrategyPositionSnapshot).where(
            PyhronStrategyPositionSnapshot.quantity > 0,
        )
        if strategy_id:
            stmt = stmt.where(PyhronStrategyPositionSnapshot.strategy_id == strategy_id)
        if symbol:
            stmt = stmt.where(PyhronStrategyPositionSnapshot.symbol == symbol)

        result = await session.execute(stmt)
        positions = result.scalars().all()

    # Compute total market value for weight calculation
    total_mv = sum(p.market_value or Decimal("0") for p in positions)

    return [
        PositionResponse(
            symbol=p.symbol,
            exchange=p.exchange or "IDX",
            strategy_id=p.strategy_id,
            quantity=p.quantity,
            avg_entry_price=p.avg_entry_price or Decimal("0"),
            current_price=p.current_price or Decimal("0"),
            unrealized_pnl=p.unrealized_pnl or Decimal("0"),
            market_value=p.market_value or Decimal("0"),
            weight_pct=float((p.market_value or Decimal("0")) / total_mv * 100) if total_mv else 0.0,
        )
        for p in positions
    ]


# Orders
@router.get("/orders", response_model=list[OrderResponse])
async def get_orders(
    strategy_id: str | None = Query(None),
    symbol: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[OrderResponse]:
    """Get order history with filters."""
    async with get_session() as session:
        stmt = select(PyhronOrderLifecycleRecord).order_by(
            PyhronOrderLifecycleRecord.created_at.desc(),
        )
        if strategy_id:
            stmt = stmt.where(PyhronOrderLifecycleRecord.strategy_id == strategy_id)
        if symbol:
            stmt = stmt.where(PyhronOrderLifecycleRecord.symbol == symbol)
        if status_filter:
            try:
                status_enum = OrderStatusEnum(status_filter.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}. "
                    f"Valid values: {[s.value for s in OrderStatusEnum]}",
                )
            stmt = stmt.where(PyhronOrderLifecycleRecord.status == status_enum)
        stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        orders = result.scalars().all()

    return [
        OrderResponse(
            client_order_id=o.client_order_id,
            strategy_id=o.strategy_id,
            symbol=o.symbol,
            side=o.side.value if hasattr(o.side, "value") else o.side,
            order_type=o.order_type.value if hasattr(o.order_type, "value") else o.order_type,
            quantity=o.quantity,
            filled_quantity=o.filled_quantity or 0,
            limit_price=o.limit_price,
            status=o.status.value if hasattr(o.status, "value") else o.status,
            created_at=o.created_at,
        )
        for o in orders
    ]


# P&L
@router.get("/pnl", response_model=list[PnLResponse])
async def get_daily_pnl(
    days: int = Query(30, ge=1, le=365),
    strategy_id: str | None = Query(None),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[PnLResponse]:
    """Get daily P&L summary across all strategies or a specific one."""
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)

    async with get_session() as session:
        # Aggregate positions for current snapshot
        pos_stmt = select(
            func.sum(PyhronStrategyPositionSnapshot.market_value).label("total_equity"),
            func.sum(PyhronStrategyPositionSnapshot.realized_pnl).label("realized_pnl"),
            func.sum(PyhronStrategyPositionSnapshot.unrealized_pnl).label("unrealized_pnl"),
        )
        if strategy_id:
            pos_stmt = pos_stmt.where(PyhronStrategyPositionSnapshot.strategy_id == strategy_id)
        pos_result = await session.execute(pos_stmt)
        pos_row = pos_result.one_or_none()

        total_equity = (pos_row.total_equity if pos_row else None) or Decimal("0")
        realized = (pos_row.realized_pnl if pos_row else None) or Decimal("0")
        unrealized = (pos_row.unrealized_pnl if pos_row else None) or Decimal("0")

        # Get daily fill aggregates for recent history
        fill_stmt = select(
            func.date_trunc("day", PyhronOrderLifecycleRecord.filled_at).label("fill_date"),
            func.count().label("fills"),
        ).where(
            PyhronOrderLifecycleRecord.filled_at >= cutoff,
            PyhronOrderLifecycleRecord.status.in_([OrderStatusEnum.FILLED, OrderStatusEnum.PARTIAL_FILL]),
        )
        if strategy_id:
            fill_stmt = fill_stmt.where(PyhronOrderLifecycleRecord.strategy_id == strategy_id)
        fill_stmt = fill_stmt.group_by("fill_date").order_by("fill_date")

        fill_result = await session.execute(fill_stmt)
        fill_rows = fill_result.all()

    # Build response: current snapshot as today, plus historical fill dates
    results: list[PnLResponse] = []
    total_pnl = realized + unrealized

    # Add today's snapshot
    results.append(
        PnLResponse(
            date=datetime.now(tz=UTC).strftime("%Y-%m-%d"),
            total_equity=total_equity,
            total_pnl=total_pnl,
            realized_pnl=realized,
            unrealized_pnl=unrealized,
        )
    )

    # Add historical fill dates as placeholders (actual daily PnL
    # requires an equity curve table; this shows trading activity)
    for row in fill_rows:
        if row.fill_date:
            d = row.fill_date.strftime("%Y-%m-%d") if hasattr(row.fill_date, "strftime") else str(row.fill_date)
            if d != results[0].date:
                results.append(
                    PnLResponse(
                        date=d,
                        total_equity=Decimal("0"),
                        total_pnl=Decimal("0"),
                        realized_pnl=Decimal("0"),
                        unrealized_pnl=Decimal("0"),
                    )
                )

    return results


# Circuit Breaker
@router.get("/circuit-breaker/status", response_model=list[CircuitBreakerStatus])
async def get_circuit_breaker_status(
    _user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> list[CircuitBreakerStatus]:
    """Get circuit breaker status for all active strategies."""
    async with get_session() as session:
        stmt = select(PyhronStrategyPositionSnapshot.strategy_id).distinct()
        result = await session.execute(stmt)
        strategy_ids = [row[0] for row in result.all()]

    cb_manager = CircuitBreakerStateManager()
    statuses: list[CircuitBreakerStatus] = []

    for sid in strategy_ids:
        state = await cb_manager.get_state(sid)
        tripped_at = None
        if state.activated_at:
            with contextlib.suppress(ValueError, TypeError):
                tripped_at = datetime.fromisoformat(state.activated_at)
        statuses.append(
            CircuitBreakerStatus(
                strategy_id=sid,
                is_tripped=state.is_active,
                tripped_at=tripped_at,
                reason=state.reason.value if state.reason else None,
            )
        )

    return statuses


@router.post("/circuit-breaker/clear")
async def clear_circuit_breaker(
    body: CircuitBreakerClearRequest,
    user: TokenPayload = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Clear a tripped circuit breaker. Requires admin role and audit reason."""
    cb_manager = CircuitBreakerStateManager()
    was_active = await cb_manager.resume(body.strategy_id, reason=body.reason)

    logger.info(
        "circuit_breaker_cleared",
        strategy_id=body.strategy_id,
        reason=body.reason,
        user=user.sub,
        was_active=was_active,
    )
    return {
        "status": "cleared" if was_active else "not_active",
        "strategy_id": body.strategy_id,
        "cleared_at": datetime.now(tz=UTC).isoformat(),
    }
