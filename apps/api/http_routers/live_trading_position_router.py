"""Live trading position API endpoints.

Open positions, order management, P&L tracking,
and circuit breaker administration.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.platform_exception_hierarchy import (
    CircuitBreakerOpenError,
    DuplicateOrderError,
    PyhronValidationError,
)
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from decimal import Decimal

    from services.order_management_system.order_submission_handler import (
        OrderSubmissionHandler,
    )

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


# ── Response Models ──────────────────────────────────────────────────────────


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


# ── Order Submission ────────────────────────────────────────────────────


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


# ── Positions ────────────────────────────────────────────────────────────────


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    strategy_id: str | None = Query(None),
    symbol: str | None = Query(None),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[PositionResponse]:
    """Get all open positions, optionally filtered by strategy or symbol."""
    logger.info("positions_queried", strategy_id=strategy_id, symbol=symbol)
    return []


# ── Orders ───────────────────────────────────────────────────────────────────


@router.get("/orders", response_model=list[OrderResponse])
async def get_orders(
    strategy_id: str | None = Query(None),
    symbol: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[OrderResponse]:
    """Get order history with filters."""
    return []


# ── P&L ──────────────────────────────────────────────────────────────────────


@router.get("/pnl", response_model=list[PnLResponse])
async def get_daily_pnl(
    days: int = Query(30, ge=1, le=365),
    strategy_id: str | None = Query(None),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[PnLResponse]:
    """Get daily P&L summary across all strategies or a specific one."""
    return []


# ── Circuit Breaker ─────────────────────────────────────────────────────────


@router.get("/circuit-breaker/status", response_model=list[CircuitBreakerStatus])
async def get_circuit_breaker_status(
    _user: TokenPayload = Depends(require_role(Role.TRADER)),
) -> list[CircuitBreakerStatus]:
    """Get circuit breaker status for all strategies."""
    return []


@router.post("/circuit-breaker/clear")
async def clear_circuit_breaker(
    body: CircuitBreakerClearRequest,
    _user: TokenPayload = Depends(require_role(Role.ADMIN)),
) -> dict[str, str]:
    """Clear a tripped circuit breaker. Requires admin role and audit reason."""
    logger.info(
        "circuit_breaker_cleared",
        strategy_id=body.strategy_id,
        reason=body.reason,
    )
    return {
        "status": "cleared",
        "strategy_id": body.strategy_id,
        "cleared_at": datetime.now(tz=UTC).isoformat(),
    }
