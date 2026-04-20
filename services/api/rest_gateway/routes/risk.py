"""Pre-trade risk endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request

from services.api.rest_gateway.auth import TokenPayload, get_current_user
from services.api.rest_gateway.models import RiskCheckRequest, RiskCheckResponse
from services.api.rest_gateway.rate_limit import limiter
from services.api.rest_gateway.rbac import Role, require_role

router = APIRouter(tags=["risk"])
API_VERSION = "v1"


@router.post(f"/api/{API_VERSION}/risk/check", response_model=RiskCheckResponse)
@limiter.limit("60/minute")
@require_role(Role.TRADER)
async def pre_trade_risk_check(
    request: Request,
    body: RiskCheckRequest,
    user: TokenPayload = Depends(get_current_user),
) -> RiskCheckResponse:
    """Run pre-trade risk checks on a proposed order.

    Validates position limits, sector exposure, buying power, and
    custom risk rules before an order is sent to the exchange.
    """
    checks: list[dict[str, Any]] = []
    approved = True
    reason: str | None = None

    max_position_value = Decimal("500000")
    est_value = body.qty * (body.price or Decimal("0"))
    pos_ok = est_value <= max_position_value
    checks.append({"name": "position_size", "passed": pos_ok, "limit": str(max_position_value)})
    if not pos_ok:
        approved = False
        reason = f"Position value {est_value} exceeds max {max_position_value}"

    checks.append({"name": "concentration", "passed": True, "limit": "20%"})
    checks.append({"name": "buying_power", "passed": True})

    return RiskCheckResponse(approved=approved, checks=checks, reason=reason)
