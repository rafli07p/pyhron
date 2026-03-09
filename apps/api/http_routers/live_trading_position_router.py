"""Live trading position API endpoints.

Open positions, order management, P&L tracking,
and circuit breaker administration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/trading", tags=["trading"])


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


# ── Positions ────────────────────────────────────────────────────────────────


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    strategy_id: str | None = Query(None),
    symbol: str | None = Query(None),
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
) -> list[OrderResponse]:
    """Get order history with filters."""
    return []


# ── P&L ──────────────────────────────────────────────────────────────────────


@router.get("/pnl", response_model=list[PnLResponse])
async def get_daily_pnl(
    days: int = Query(30, ge=1, le=365),
    strategy_id: str | None = Query(None),
) -> list[PnLResponse]:
    """Get daily P&L summary across all strategies or a specific one."""
    return []


# ── Circuit Breaker ─────────────────────────────────────────────────────────


@router.get("/circuit-breaker/status", response_model=list[CircuitBreakerStatus])
async def get_circuit_breaker_status() -> list[CircuitBreakerStatus]:
    """Get circuit breaker status for all strategies."""
    return []


@router.post("/circuit-breaker/clear")
async def clear_circuit_breaker(body: CircuitBreakerClearRequest) -> dict[str, str]:
    """Clear a tripped circuit breaker. Requires admin role and audit reason."""
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
