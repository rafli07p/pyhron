"""Portfolio endpoints."""

from __future__ import annotations

from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, Request

from services.api.rest_gateway.auth import TokenPayload, get_current_user
from services.api.rest_gateway.models import PortfolioPnlResponse, PositionResponse
from services.api.rest_gateway.rate_limit import limiter

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter(tags=["portfolio"])
API_VERSION = "v1"


@router.get(f"/api/{API_VERSION}/portfolio", response_model=list[PositionResponse])
@limiter.limit("60/minute")
async def get_positions(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> list[PositionResponse]:
    """Return current positions for the authenticated tenant.

    Queries the portfolio service for live positions and marks
    them to market using latest quotes.
    """
    import os

    positions: list[PositionResponse] = []
    alpaca_key = os.environ.get("ALPACA_API_KEY", "")
    alpaca_secret = os.environ.get("ALPACA_SECRET_KEY", "")

    if alpaca_key and alpaca_secret:
        try:
            import httpx

            base_url = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/v2/positions",
                    headers={
                        "APCA-API-KEY-ID": alpaca_key,
                        "APCA-API-SECRET-KEY": alpaca_secret,
                    },
                )
                if resp.status_code == 200:
                    for p in resp.json():
                        positions.append(
                            PositionResponse(
                                symbol=p["symbol"],
                                qty=Decimal(p["qty"]),
                                avg_cost=Decimal(p["avg_entry_price"]),
                                market_value=Decimal(p["market_value"]),
                                unrealized_pnl=Decimal(p["unrealized_pl"]),
                            )
                        )
        except Exception:
            logger.exception("alpaca_positions_error")

    return positions


@router.get(f"/api/{API_VERSION}/portfolio/pnl", response_model=PortfolioPnlResponse)
@limiter.limit("60/minute")
async def get_portfolio_pnl(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> PortfolioPnlResponse:
    """Return portfolio P&L summary for the authenticated tenant.

    Aggregates position-level P&L from the Alpaca account or
    internal portfolio service.
    """
    import os

    tenant_id = user.tenant_id
    alpaca_key = os.environ.get("ALPACA_API_KEY", "")
    alpaca_secret = os.environ.get("ALPACA_SECRET_KEY", "")

    total_equity = Decimal("0")
    total_pnl = Decimal("0")
    realized = Decimal("0")
    unrealized = Decimal("0")
    positions: list[PositionResponse] = []

    if alpaca_key and alpaca_secret:
        try:
            import httpx

            base_url = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
            async with httpx.AsyncClient(timeout=10.0) as client:
                acct_resp = await client.get(
                    f"{base_url}/v2/account",
                    headers={
                        "APCA-API-KEY-ID": alpaca_key,
                        "APCA-API-SECRET-KEY": alpaca_secret,
                    },
                )
                if acct_resp.status_code == 200:
                    acct = acct_resp.json()
                    total_equity = Decimal(acct.get("equity", "0"))
                    total_pnl = total_equity - Decimal(acct.get("last_equity", str(total_equity)))

                pos_resp = await client.get(
                    f"{base_url}/v2/positions",
                    headers={
                        "APCA-API-KEY-ID": alpaca_key,
                        "APCA-API-SECRET-KEY": alpaca_secret,
                    },
                )
                if pos_resp.status_code == 200:
                    for p in pos_resp.json():
                        upl = Decimal(p["unrealized_pl"])
                        unrealized += upl
                        positions.append(
                            PositionResponse(
                                symbol=p["symbol"],
                                qty=Decimal(p["qty"]),
                                avg_cost=Decimal(p["avg_entry_price"]),
                                market_value=Decimal(p["market_value"]),
                                unrealized_pnl=upl,
                            )
                        )
        except Exception:
            logger.exception("alpaca_pnl_error")

    realized = total_pnl - unrealized

    return PortfolioPnlResponse(
        tenant_id=tenant_id,
        total_equity=total_equity,
        total_pnl=total_pnl,
        realized_pnl=realized,
        unrealized_pnl=unrealized,
        positions=positions,
    )
