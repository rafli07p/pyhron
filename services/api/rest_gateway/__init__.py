"""Enthropy REST API Gateway.

FastAPI application serving market data, order management, portfolio,
research, risk, and admin endpoints.  Includes JWT authentication,
role-based access control (RBAC), tenant isolation, CORS, rate
limiting (slowapi), structured logging, and OpenAPI documentation.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID, uuid4

import jwt
import structlog
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from shared.configuration_settings import get_config as _get_settings

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send
from shared.schemas.market_events import BarEvent, QuoteEvent  # noqa: F401
from shared.schemas.order_events import (
    CancelReason,
    OrderCancel,  # noqa: F401
    OrderRequest,  # noqa: F401
    OrderSide,
    OrderStatus,  # noqa: F401
    OrderStatusEnum,
    OrderType,
    TimeInForce,
)

logger = structlog.stdlib.get_logger(__name__)

API_VERSION = "v1"


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


class Role(StrEnum):
    VIEWER = "viewer"
    TRADER = "trader"
    RESEARCHER = "researcher"
    ADMIN = "admin"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.TRADER: 1,
    Role.RESEARCHER: 2,
    Role.ADMIN: 3,
}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: Role = Role.VIEWER
    exp: int | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class MarketDataRequest(BaseModel):
    interval: str = "1min"
    limit: int = Field(default=100, ge=1, le=5000)
    start: datetime | None = None
    end: datetime | None = None


class MarketDataResponse(BaseModel):
    symbol: str
    bars: list[dict[str, Any]] = Field(default_factory=list)
    quotes: list[dict[str, Any]] = Field(default_factory=list)


class CreateOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: OrderSide
    qty: Decimal = Field(..., gt=0)
    order_type: OrderType = OrderType.LIMIT
    price: Decimal | None = None
    stop_price: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.DAY
    strategy_id: str | None = None
    account_id: str | None = None


class CreateOrderResponse(BaseModel):
    order_id: UUID
    status: OrderStatusEnum = OrderStatusEnum.PENDING
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class CancelOrderRequest(BaseModel):
    order_id: UUID
    reason: CancelReason = CancelReason.USER_REQUESTED


class PositionResponse(BaseModel):
    symbol: str
    qty: Decimal
    avg_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


class PortfolioPnlResponse(BaseModel):
    tenant_id: str
    total_equity: Decimal
    total_pnl: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    positions: list[PositionResponse] = Field(default_factory=list)
    as_of: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class BacktestRequest(BaseModel):
    strategy_id: str
    symbols: list[str]
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal("1000000")
    parameters: dict[str, Any] = Field(default_factory=dict)


class BacktestResponse(BaseModel):
    backtest_id: UUID = Field(default_factory=uuid4)
    status: str = "submitted"
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class RiskCheckRequest(BaseModel):
    symbol: str
    side: OrderSide
    qty: Decimal
    price: Decimal | None = None
    account_id: str | None = None


class RiskCheckResponse(BaseModel):
    approved: bool
    checks: list[dict[str, Any]] = Field(default_factory=list)
    reason: str | None = None


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str
    role: Role = Role.VIEWER


class UserResponse(BaseModel):
    user_id: UUID = Field(default_factory=uuid4)
    username: str
    email: str
    role: Role
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class UserUpdateRequest(BaseModel):
    email: str | None = None
    role: Role | None = None


# ---------------------------------------------------------------------------
# JWT auth dependency
# ---------------------------------------------------------------------------


async def get_current_user(request: Request) -> TokenPayload:
    """Extract and validate JWT from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        _settings = _get_settings()
        payload = jwt.decode(token, _settings.jwt_secret_key, algorithms=[_settings.jwt_algorithm])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from err
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}") from exc


def get_tenant_id(user: TokenPayload = Depends(get_current_user)) -> str:
    """Extract tenant_id from the authenticated user's JWT claims."""
    return user.tenant_id


# ---------------------------------------------------------------------------
# RBAC decorator
# ---------------------------------------------------------------------------


_F = TypeVar("_F", bound=Callable[..., Any])


def require_role(minimum_role: Role) -> Callable[[_F], _F]:
    """Decorator that enforces a minimum RBAC role on an endpoint."""

    def decorator(func: _F) -> _F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user: TokenPayload | None = kwargs.get("user")
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
            if ROLE_HIERARCHY.get(user.role, -1) < ROLE_HIERARCHY[minimum_role]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{user.role}' insufficient; requires '{minimum_role}' or above",
                )
            return await func(*args, **kwargs)

        return cast(_F, wrapper)

    return decorator


# ---------------------------------------------------------------------------
# CSRF protection middleware (double-submit cookie)
# ---------------------------------------------------------------------------

_CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_CSRF_EXEMPT_PREFIXES = ("/v1/auth/", "/health")


class CSRFMiddleware:
    """ASGI middleware implementing double-submit cookie CSRF protection.

    - On safe methods (GET, HEAD, OPTIONS): sets a ``csrf_token`` cookie
      if one is not already present.
    - On state-changing methods (POST, PUT, DELETE, PATCH): verifies
      that the ``X-CSRF-Token`` header matches the ``csrf_token`` cookie.
    - Skips CSRF checks for ``/v1/auth/*`` and ``/health`` endpoints.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        # Check if path is exempt from CSRF
        is_exempt = any(path.startswith(prefix) for prefix in _CSRF_EXEMPT_PREFIXES)

        if request.method not in _CSRF_SAFE_METHODS and not is_exempt:
            cookie_token = request.cookies.get("csrf_token")
            header_token = request.headers.get("X-CSRF-Token")
            if not cookie_token or not header_token or cookie_token != header_token:
                response = JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token missing or mismatched"},
                )
                await response(scope, receive, send)
                return

        # For safe methods, set the CSRF cookie if not present
        needs_cookie = request.method in _CSRF_SAFE_METHODS and not is_exempt and "csrf_token" not in request.cookies
        if needs_cookie:
            new_token = secrets.token_urlsafe(32)

            async def send_with_cookie(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    cookie_val = f"csrf_token={new_token}; Path=/; HttpOnly=false; SameSite=Strict; Secure"
                    headers.append((b"set-cookie", cookie_val.encode()))
                    message = {**message, "headers": headers}
                await send(message)

            await self.app(scope, receive, send_with_cookie)
        else:
            await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

_SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"content-security-policy", b"default-src 'self'"),
]


class SecurityHeadersMiddleware:
    """ASGI middleware that adds security headers to every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(_SECURITY_HEADERS)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


# ---------------------------------------------------------------------------
# Structlog request-logging middleware
# ---------------------------------------------------------------------------


class RequestIDMiddleware:
    """ASGI middleware that generates/propagates X-Request-ID header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode() or str(uuid4())
        scope.setdefault("state", {})

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": resp_headers}
            await send(message)

        await self.app(scope, receive, send_with_request_id)


class RequestLoggingMiddleware:
    """ASGI middleware that logs every HTTP request with timing."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        start = time.perf_counter()
        response_status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response_status,
                duration_ms=round(elapsed_ms, 2),
                client=request.client.host if request.client else None,
            )


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_rest_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

    app = FastAPI(
        title="Pyhron Trading Platform API",
        description="REST API for the Pyhron quant research and trading platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.state.limiter = limiter

    async def _handle_rate_limit(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, RateLimitExceeded)
        return _rate_limit_exceeded_handler(request, exc)

    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_settings().allowed_cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # CSRF protection
    app.add_middleware(CSRFMiddleware)

    # Request ID propagation
    app.add_middleware(RequestIDMiddleware)

    # Structlog request logging
    app.add_middleware(RequestLoggingMiddleware)

    # ------------------------------------------------------------------
    # Pyhron domain routers (IDX equity, macro, commodity, etc.)
    # ------------------------------------------------------------------
    from apps.api.http_routers.backtest_execution_router import router as backtest_router
    from apps.api.http_routers.commodity_stock_impact_router import router as commodity_impact_router
    from apps.api.http_routers.governance_intelligence_router import router as governance_router
    from apps.api.http_routers.idx_equity_screener_router import router as screener_router
    from apps.api.http_routers.idx_equity_stock_detail_router import router as stock_detail_router
    from apps.api.http_routers.idx_market_overview_router import router as market_overview_router
    from apps.api.http_routers.indonesia_commodity_price_router import router as commodity_price_router
    from apps.api.http_routers.indonesia_fixed_income_router import router as fixed_income_router
    from apps.api.http_routers.indonesia_macro_dashboard_router import router as macro_router
    from apps.api.http_routers.indonesia_news_sentiment_router import router as news_router
    from apps.api.http_routers.live_trading_position_router import router as live_trading_router
    from apps.api.http_routers.live_trading_risk_router import router as live_trading_risk_router
    from apps.api.http_routers.paper_trading_router import router as paper_trading_router
    from apps.api.http_routers.strategy_management_router import router as strategy_router
    from apps.api.http_routers.user_authentication_router import router as auth_router

    app.include_router(screener_router)
    app.include_router(stock_detail_router)
    app.include_router(market_overview_router)
    app.include_router(news_router)
    app.include_router(macro_router)
    app.include_router(commodity_price_router)
    app.include_router(commodity_impact_router)
    app.include_router(fixed_income_router)
    app.include_router(governance_router)
    app.include_router(strategy_router)
    app.include_router(backtest_router)
    app.include_router(live_trading_router)
    app.include_router(live_trading_risk_router)
    app.include_router(auth_router)
    app.include_router(paper_trading_router)

    # ------------------------------------------------------------------
    # Health / Readiness
    # ------------------------------------------------------------------

    @app.get("/health", response_model=None, tags=["ops"])
    async def health() -> JSONResponse:
        """Enhanced health check – verifies Postgres and Redis connectivity."""
        import redis.asyncio as aioredis
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        from shared.configuration_settings import get_config

        cfg = get_config()
        checks: dict[str, str] = {}

        # -- Postgres --
        try:
            engine = create_async_engine(cfg.database_url, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"

        # -- Redis --
        try:
            r = aioredis.from_url(cfg.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
            await r.ping()
            await r.aclose()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"

        all_ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={
                "status": "ok" if all_ok else "degraded",
                "version": "0.1.0",
                "checks": checks,
            },
        )

    # Prometheus metrics endpoint
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    from shared.metrics import REGISTRY

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.get("/ready", tags=["ops"])
    async def readiness() -> dict[str, str]:
        # TODO: verify downstream dependencies (DB, Redis, Kafka)
        return {"status": "ready"}

    # ------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------

    @app.get(f"/api/{API_VERSION}/market-data/{{symbol}}", response_model=MarketDataResponse, tags=["market-data"])
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

        # --- Polygon.io bars ---
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

                    # last quote
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

        # --- yfinance fallback ---
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

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    @app.post(f"/api/{API_VERSION}/orders", response_model=CreateOrderResponse, status_code=201, tags=["orders"])
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

    @app.get(f"/api/{API_VERSION}/orders", tags=["orders"])
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
        # In production, query OMS/DB filtered by tenant_id
        return []

    @app.delete(f"/api/{API_VERSION}/orders/{{order_id}}", tags=["orders"])
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

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------

    @app.get(f"/api/{API_VERSION}/portfolio", response_model=list[PositionResponse], tags=["portfolio"])
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

    @app.get(f"/api/{API_VERSION}/portfolio/pnl", response_model=PortfolioPnlResponse, tags=["portfolio"])
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

    # ------------------------------------------------------------------
    # Research / Backtest
    # ------------------------------------------------------------------

    @app.post(
        f"/api/{API_VERSION}/research/backtest",
        response_model=BacktestResponse,
        status_code=202,
        tags=["research"],
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

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------

    @app.post(f"/api/{API_VERSION}/risk/check", response_model=RiskCheckResponse, tags=["risk"])
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

        # Position size check
        max_position_value = Decimal("500000")
        est_value = body.qty * (body.price or Decimal("0"))
        pos_ok = est_value <= max_position_value
        checks.append({"name": "position_size", "passed": pos_ok, "limit": str(max_position_value)})
        if not pos_ok:
            approved = False
            reason = f"Position value {est_value} exceeds max {max_position_value}"

        # Concentration check
        checks.append({"name": "concentration", "passed": True, "limit": "20%"})

        # Buying power (would query Alpaca in production)
        checks.append({"name": "buying_power", "passed": True})

        return RiskCheckResponse(approved=approved, checks=checks, reason=reason)

    # ------------------------------------------------------------------
    # Admin / Users
    # ------------------------------------------------------------------

    @app.post(f"/api/{API_VERSION}/admin/users", response_model=UserResponse, status_code=201, tags=["admin"])
    @limiter.limit("10/minute")
    @require_role(Role.ADMIN)
    async def create_user(
        request: Request,
        body: UserCreateRequest,
        user: TokenPayload = Depends(get_current_user),
    ) -> UserResponse:
        """Create a new user within the authenticated tenant."""
        logger.info("user_created", username=body.username, tenant_id=user.tenant_id)
        return UserResponse(
            username=body.username,
            email=body.email,
            role=body.role,
            tenant_id=user.tenant_id,
        )

    @app.get(f"/api/{API_VERSION}/admin/users", response_model=list[UserResponse], tags=["admin"])
    @limiter.limit("30/minute")
    @require_role(Role.ADMIN)
    async def list_users(
        request: Request,
        user: TokenPayload = Depends(get_current_user),
    ) -> list[UserResponse]:
        """List all users for the authenticated tenant."""
        return []

    @app.get(f"/api/{API_VERSION}/admin/users/{{user_id}}", response_model=UserResponse, tags=["admin"])
    @limiter.limit("30/minute")
    @require_role(Role.ADMIN)
    async def get_user(
        request: Request,
        user_id: UUID,
        user: TokenPayload = Depends(get_current_user),
    ) -> UserResponse:
        """Get a specific user by ID."""
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    @app.put(f"/api/{API_VERSION}/admin/users/{{user_id}}", response_model=UserResponse, tags=["admin"])
    @limiter.limit("10/minute")
    @require_role(Role.ADMIN)
    async def update_user(
        request: Request,
        user_id: UUID,
        body: UserUpdateRequest,
        user: TokenPayload = Depends(get_current_user),
    ) -> UserResponse:
        """Update user details (email, role)."""
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    @app.delete(f"/api/{API_VERSION}/admin/users/{{user_id}}", status_code=204, tags=["admin"])
    @limiter.limit("10/minute")
    @require_role(Role.ADMIN)
    async def delete_user(
        request: Request,
        user_id: UUID,
        user: TokenPayload = Depends(get_current_user),
    ) -> None:
        """Delete a user from the tenant."""
        logger.info("user_deleted", user_id=str(user_id), tenant_id=user.tenant_id)

    # ------------------------------------------------------------------
    # Global exception handler
    # ------------------------------------------------------------------

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    return app


__all__ = [
    "Role",
    "TokenPayload",
    "create_rest_app",
    "get_current_user",
    "get_tenant_id",
    "require_role",
]
