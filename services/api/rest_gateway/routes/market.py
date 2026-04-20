"""Market data endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query, Request

from services.api.rest_gateway.auth import TokenPayload, get_current_user
from services.api.rest_gateway.models import MarketDataResponse
from services.api.rest_gateway.rate_limit import limiter

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter(tags=["market-data"])
API_VERSION = "v1"


@router.get(f"/api/{API_VERSION}/market-data/{{symbol}}", response_model=MarketDataResponse)
@limiter.limit("60/minute")
async def get_market_data(
    request: Request,
    symbol: str,
    interval: str = Query("1min", description="Bar interval (1min, 5min, 1hour, 1day)"),
    limit: int = Query(100, ge=1, le=5000),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    user: TokenPayload = Depends(get_current_user),
) -> MarketDataResponse:
    """Retrieve OHLCV bars and latest quotes for a symbol.

    Uses Polygon.io REST API for bar aggregates and last-quote.
    Falls back to yfinance for historical data when Polygon
    returns no results.
    """
    import os

    tenant_id = user.tenant_id
    log = logger.bind(symbol=symbol, tenant_id=tenant_id)

    bars: list[dict[str, Any]] = []
    quotes: list[dict[str, Any]] = []

    # Polygon.io bars
    polygon_key = os.environ.get("POLYGON_API_KEY", "")
    if polygon_key:
        try:
            import httpx

            _interval_map = {
                "1min": ("1", "minute"),
                "5min": ("5", "minute"),
                "15min": ("15", "minute"),
                "1hour": ("1", "hour"),
                "1day": ("1", "day"),
            }
            multiplier, timespan = _interval_map.get(interval, ("1", "minute"))
            from_date = (start or datetime(2024, 1, 1, tzinfo=UTC)).strftime("%Y-%m-%d")
            to_date = (end or datetime.now(tz=UTC)).strftime("%Y-%m-%d")

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range"
                    f"/{multiplier}/{timespan}/{from_date}/{to_date}",
                    params={"adjusted": "true", "sort": "desc", "limit": limit, "apiKey": polygon_key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", []):
                        bars.append(
                            {
                                "open": r["o"],
                                "high": r["h"],
                                "low": r["l"],
                                "close": r["c"],
                                "volume": r["v"],
                                "vwap": r.get("vw"),
                                "timestamp": r["t"],
                                "bar_count": r.get("n"),
                            }
                        )
                else:
                    log.warning("polygon_bars_error", status=resp.status_code, body=resp.text[:200])

                quote_resp = await client.get(
                    f"https://api.polygon.io/v3/quotes/{symbol}",
                    params={"limit": 1, "sort": "timestamp", "order": "desc", "apiKey": polygon_key},
                )
                if quote_resp.status_code == 200:
                    for q in quote_resp.json().get("results", []):
                        quotes.append(
                            {
                                "bid": q.get("bid_price", 0),
                                "ask": q.get("ask_price", 0),
                                "bid_size": q.get("bid_size", 0),
                                "ask_size": q.get("ask_size", 0),
                                "timestamp": q.get("participant_timestamp"),
                            }
                        )
        except Exception:
            log.exception("polygon_api_error")

    # yfinance fallback
    if not bars:
        try:
            import yfinance as yf

            _yf_interval_map = {"1min": "1m", "5min": "5m", "15min": "15m", "1hour": "1h", "1day": "1d"}
            yf_interval = _yf_interval_map.get(interval, "1d")
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d", interval=yf_interval)
            for ts, row in hist.iterrows():
                bars.append(
                    {
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                        "timestamp": int(ts.timestamp() * 1000),
                    }
                )
            bars = bars[-limit:]
        except Exception:
            log.exception("yfinance_fallback_error")

    return MarketDataResponse(symbol=symbol, bars=bars, quotes=quotes)
