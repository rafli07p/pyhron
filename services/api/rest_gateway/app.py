"""FastAPI application factory for the Pyhron REST gateway."""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette import status

from services.api.logging import RequestLoggingMiddleware
from services.api.rest_gateway.middleware import (
    CSRFMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from services.api.rest_gateway.rate_limit import limiter
from services.api.rest_gateway.routes import admin, market, orders, portfolio, research, risk
from shared.configuration_settings import get_config as _get_settings

logger = structlog.stdlib.get_logger(__name__)


def create_rest_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
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

    # CORS — reject wildcard origins when credentials are enabled
    _cors_origins = [o.strip() for o in _get_settings().allowed_cors_origins.split(",") if o.strip()]
    if "*" in _cors_origins and _get_settings().is_production:
        logger.error("cors_wildcard_blocked", message="Wildcard CORS origin blocked in production")
        _cors_origins = []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Pyhron domain routers (IDX equity, macro, commodity, etc.)
    from apps.api.http_routers.backtest_execution_router import router as backtest_router
    from apps.api.http_routers.commodity_stock_impact_router import router as commodity_impact_router
    from apps.api.http_routers.execution_algos_router import router as execution_algos_router
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
    from apps.api.http_routers.ml_signals_router import router as ml_signals_router
    from apps.api.http_routers.paper_trading_router import router as paper_trading_router
    from apps.api.http_routers.portfolio_optimizer_router import router as portfolio_optimizer_router
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
    app.include_router(execution_algos_router)
    app.include_router(portfolio_optimizer_router)
    app.include_router(ml_signals_router)

    # REST gateway domain routers
    app.include_router(market.router)
    app.include_router(orders.router)
    app.include_router(portfolio.router)
    app.include_router(research.router)
    app.include_router(risk.router)
    app.include_router(admin.router)

    # Ops endpoints

    @app.get("/health", response_model=None, tags=["ops"])
    async def health() -> JSONResponse:
        """Enhanced health check – verifies Postgres and Redis connectivity."""
        import redis.asyncio as aioredis
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        from shared.configuration_settings import get_config

        cfg = get_config()
        checks: dict[str, str] = {}

        try:
            engine = create_async_engine(cfg.database_url, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"

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

    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    from shared.metrics import REGISTRY

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.get("/ready", response_model=None, tags=["ops"])
    async def readiness() -> JSONResponse:
        """Readiness probe – verifies Postgres, Redis, and Kafka connectivity."""
        import redis.asyncio as aioredis
        from aiokafka import AIOKafkaProducer
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        from shared.configuration_settings import get_config

        cfg = get_config()
        checks: dict[str, str] = {}

        try:
            engine = create_async_engine(cfg.database_url, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"

        try:
            r = aioredis.from_url(cfg.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
            await r.ping()
            await r.aclose()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"

        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=cfg.kafka_bootstrap_servers,
                request_timeout_ms=5000,
            )
            await producer.start()
            await producer.stop()
            checks["kafka"] = "ok"
        except Exception as exc:
            checks["kafka"] = f"error: {exc}"

        all_ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={
                "status": "ready" if all_ok else "not_ready",
                "checks": checks,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    return app
