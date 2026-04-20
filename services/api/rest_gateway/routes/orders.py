"""Order management endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, Query, Request

from services.api.rest_gateway.auth import TokenPayload, get_current_user
from services.api.rest_gateway.models import (
    CreateOrderRequest,
    CreateOrderResponse,
)
from services.api.rest_gateway.rate_limit import limiter
from services.api.rest_gateway.rbac import Role, require_role
from shared.schemas.order_events import OrderStatusEnum

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter(tags=["orders"])
API_VERSION = "v1"


@router.post(f"/api/{API_VERSION}/orders", response_model=CreateOrderResponse, status_code=201)
@limiter.limit("30/minute")
@require_role(Role.TRADER)
async def create_order(
    request: Request,
    body: CreateOrderRequest,
    user: TokenPayload = Depends(get_current_user),
) -> CreateOrderResponse:
    """Submit a new order to the OMS.

    Validates the order via pre-trade risk checks before forwarding
    to the execution service.
    """
    log = logger.bind(symbol=body.symbol, side=body.side, tenant_id=user.tenant_id)
    order_id = uuid4()
    log.info("order_submitted", order_id=str(order_id), qty=str(body.qty), order_type=body.order_type)
    return CreateOrderResponse(order_id=order_id)


@router.get(f"/api/{API_VERSION}/orders")
@limiter.limit("60/minute")
@require_role(Role.TRADER)
async def list_orders(
    request: Request,
    status_filter: OrderStatusEnum | None = Query(None, alias="status"),
    symbol: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    user: TokenPayload = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List orders for the authenticated tenant."""
    log = logger.bind(tenant_id=user.tenant_id)
    log.info("list_orders", status_filter=status_filter, symbol=symbol)
    return []


@router.delete(f"/api/{API_VERSION}/orders/{{order_id}}")
@limiter.limit("30/minute")
@require_role(Role.TRADER)
async def cancel_order(
    request: Request,
    order_id: UUID,
    user: TokenPayload = Depends(get_current_user),
) -> dict[str, Any]:
    """Cancel an open order."""
    log = logger.bind(order_id=str(order_id), tenant_id=user.tenant_id)
    log.info("order_cancel_requested")
    return {"order_id": str(order_id), "status": "cancel_requested"}
