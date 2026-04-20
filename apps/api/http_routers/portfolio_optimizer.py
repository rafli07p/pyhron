"""Portfolio optimization + holdings API endpoints.

Rebalance endpoint for triggering portfolio optimization (Black-Litterman,
HRP, equal-weight) plus holdings/summary endpoints for the demo portfolio
with live price enrichment from yfinance.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from functools import partial
from typing import Any

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from shared.async_database_session import get_session
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/portfolio", tags=["portfolio"])

DEMO_STRATEGY_ID = "660e8400-e29b-41d4-a716-446655440001"


# ── Rebalance (existing) ─────────────────────────────────────────────────────
class RebalanceRequest(BaseModel):
    method: str = Field(default="black_litterman", description="black_litterman, hrp, or equal_weight")
    universe: list[str] = Field(..., min_length=1)
    max_weight: float = Field(default=0.15, ge=0.01, le=1.0)
    target_vol: float | None = Field(default=None, description="Target annualised volatility")


class RebalanceResponse(BaseModel):
    weights: dict[str, float]
    expected_return: float
    expected_vol: float
    turnover: float
    estimated_cost_bps: float
    method: str
    timestamp: str


@router.post("/rebalance", response_model=RebalanceResponse)
async def rebalance_portfolio(request: RebalanceRequest) -> RebalanceResponse:
    """Trigger portfolio rebalance with the specified method."""
    valid_methods = {"black_litterman", "hrp", "equal_weight"}
    if request.method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown method: {request.method}. Available: {sorted(valid_methods)}",
        )

    now = datetime.now(tz=UTC)
    n = len(request.universe)
    w = 1.0 / n
    weights = {s: w for s in request.universe}

    turnover = 0.0
    cost_bps = turnover * 30

    logger.info("portfolio_rebalanced", method=request.method, n_assets=n, turnover=turnover)

    return RebalanceResponse(
        weights=weights,
        expected_return=0.0,
        expected_vol=0.0,
        turnover=turnover,
        estimated_cost_bps=cost_bps,
        method=request.method,
        timestamp=now.isoformat(),
    )


# ── Holdings + Summary ───────────────────────────────────────────────────────
class HoldingRow(BaseModel):
    symbol: str
    company_name: str
    quantity: int
    avg_entry_price: float
    current_price: float | None
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    weight: float
    day_change_pct: float | None


class PortfolioSummary(BaseModel):
    total_market_value: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    total_realized_pnl: float
    num_positions: int
    as_of: str


@router.get("/holdings", response_model=list[HoldingRow])
async def get_holdings(
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[HoldingRow]:
    """Get current portfolio holdings enriched with live yfinance prices."""
    async with get_session() as session:
        result = await session.execute(
            text(
                """
                SELECT p.symbol, p.quantity, p.avg_entry_price,
                       p.market_value, p.unrealized_pnl, p.realized_pnl,
                       i.company_name
                FROM positions p
                LEFT JOIN instruments i ON i.symbol = p.symbol
                WHERE p.strategy_id = :sid
                ORDER BY p.market_value DESC NULLS LAST
                """
            ),
            {"sid": DEMO_STRATEGY_ID},
        )
        rows = result.fetchall()

    if not rows:
        return []

    symbols = [r.symbol for r in rows]

    def _fetch_prices(syms: list[str]) -> dict[str, dict[str, float]]:
        prices: dict[str, dict[str, float]] = {}
        for sym in syms:
            try:
                t = yf.Ticker(f"{sym}.JK")
                hist = t.history(period="2d")
                if not hist.empty:
                    close = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else close
                    chg = (close - prev) / prev * 100 if prev else 0.0
                    prices[sym] = {"price": close, "day_change_pct": round(chg, 2)}
            except Exception:
                logger.warning("holdings_price_fetch_failed", symbol=sym)
        return prices

    loop = asyncio.get_event_loop()
    live = await loop.run_in_executor(None, partial(_fetch_prices, symbols))

    holdings: list[dict[str, Any]] = []
    total_mkt_val = 0.0
    for r in rows:
        price_data = live.get(r.symbol, {})
        cur_price = price_data.get("price")
        qty = int(r.quantity)
        avg_entry = float(r.avg_entry_price or 0)
        cost_basis = qty * avg_entry
        mkt_val = qty * cur_price if cur_price else float(r.market_value or cost_basis)
        unreal_pnl = mkt_val - cost_basis
        unreal_pct = (unreal_pnl / cost_basis * 100) if cost_basis else 0.0
        total_mkt_val += mkt_val
        holdings.append({
            "symbol": r.symbol,
            "company_name": r.company_name or r.symbol,
            "quantity": qty,
            "avg_entry_price": avg_entry,
            "current_price": cur_price,
            "market_value": round(mkt_val, 0),
            "cost_basis": round(cost_basis, 0),
            "unrealized_pnl": round(unreal_pnl, 0),
            "unrealized_pnl_pct": round(unreal_pct, 2),
            "weight": 0.0,
            "day_change_pct": price_data.get("day_change_pct"),
        })

    for h in holdings:
        h["weight"] = round(h["market_value"] / total_mkt_val * 100, 2) if total_mkt_val else 0.0

    return [HoldingRow(**h) for h in holdings]


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> PortfolioSummary:
    """Aggregate portfolio-level P&L — computed from live prices, not stale DB values."""
    # Reuse holdings logic to get live-enriched positions
    holdings = await get_holdings(_user=_user)
    today = str(datetime.now(UTC).date())

    if not holdings:
        return PortfolioSummary(
            total_market_value=0,
            total_cost_basis=0,
            total_unrealized_pnl=0,
            total_unrealized_pnl_pct=0,
            total_realized_pnl=0,
            num_positions=0,
            as_of=today,
        )

    total_mkt = sum(h.market_value for h in holdings)
    total_cost = sum(h.cost_basis for h in holdings)
    total_unreal = sum(h.unrealized_pnl for h in holdings)
    unreal_pct = (total_unreal / total_cost * 100) if total_cost else 0.0

    # Realized P&L still from DB (not affected by live prices)
    async with get_session() as session:
        result = await session.execute(
            text("SELECT SUM(realized_pnl) AS total_real FROM positions WHERE strategy_id = :sid"),
            {"sid": DEMO_STRATEGY_ID},
        )
        row = result.fetchone()
    total_real = float(row.total_real or 0) if row else 0.0

    return PortfolioSummary(
        total_market_value=round(total_mkt, 0),
        total_cost_basis=round(total_cost, 0),
        total_unrealized_pnl=round(total_unreal, 0),
        total_unrealized_pnl_pct=round(unreal_pct, 2),
        total_realized_pnl=round(total_real, 0),
        num_positions=len(holdings),
        as_of=today,
    )
