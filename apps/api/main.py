"""Pyhron API — FastAPI application entrypoint.

Run with::

    uvicorn apps.api.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.redis_cache_client import close_redis
from shared.configuration_settings import get_config
from shared.structured_json_logger import get_logger

from .middleware.rate_limit import RateLimitMiddleware
from .middleware.timing import TimingMiddleware
from .routers import auth, market_data, trading

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle."""
    config = get_config()
    logger.info("api_starting", env=config.app_env, port=config.app_port)
    yield
    await close_redis()
    logger.info("api_stopped")


app = FastAPI(
    title="Pyhron",
    description="Indonesian equities algorithmic trading platform",
    version="0.1.0-alpha",
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost first) ─────────────────────────────
app.add_middleware(TimingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(trading.router)
app.include_router(market_data.router)
app.include_router(auth.router)


# ── Health ───────────────────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
async def readiness() -> dict[str, str]:
    """Readiness probe — checks downstream dependencies."""
    # In production: ping DB, Redis, Kafka
    return {"status": "ready"}
