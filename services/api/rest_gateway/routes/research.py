"""Research / backtest endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request

from services.api.rest_gateway.auth import TokenPayload, get_current_user
from services.api.rest_gateway.models import BacktestRequest, BacktestResponse
from services.api.rest_gateway.rate_limit import limiter
from services.api.rest_gateway.rbac import Role, require_role

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter(tags=["research"])
API_VERSION = "v1"


@router.post(
    f"/api/{API_VERSION}/research/backtest",
    response_model=BacktestResponse,
    status_code=202,
)
@limiter.limit("5/minute")
@require_role(Role.RESEARCHER)
async def run_backtest(
    request: Request,
    body: BacktestRequest,
    user: TokenPayload = Depends(get_current_user),
) -> BacktestResponse:
    """Submit a backtest job to the research service.

    The backtest runs asynchronously; poll the returned
    ``backtest_id`` for results.
    """
    log = logger.bind(
        tenant_id=user.tenant_id,
        strategy_id=body.strategy_id,
        symbols=body.symbols,
    )
    bt = BacktestResponse()
    log.info("backtest_submitted", backtest_id=str(bt.backtest_id))
    return bt
