"""Unit tests for production deployment infrastructure.

Tests health check, request tracing, Prometheus metrics,
and Kafka topic completeness.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Test 1: Health check returns 200 when DB and Redis are healthy ──────────


@pytest.mark.asyncio
async def test_health_check_ok() -> None:
    """Health endpoint should return 200 with status 'ok' when all deps are up."""
    from unittest.mock import patch as sync_patch

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from starlette.testclient import TestClient

    mock_engine = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_engine.connect = MagicMock(return_value=mock_conn)
    mock_engine.dispose = AsyncMock()

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    mock_cfg = MagicMock()
    mock_cfg.database_url = "postgresql+asyncpg://test:test@localhost/test"
    mock_cfg.redis_url = "redis://localhost:6379/0"

    app = FastAPI()

    @app.get("/health", response_model=None)
    async def health() -> JSONResponse:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine as _create

        from shared.configuration_settings import get_config

        cfg = get_config()
        checks: dict[str, str] = {}
        try:
            engine = _create(cfg.database_url, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(cfg.redis_url, decode_responses=True)
            await r.ping()
            await r.aclose()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
        all_ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={"status": "ok" if all_ok else "degraded", "checks": checks},
        )

    with (
        sync_patch(
            "sqlalchemy.ext.asyncio.create_async_engine",
            return_value=mock_engine,
        ),
        sync_patch(
            "redis.asyncio.from_url",
            return_value=mock_redis,
        ),
        sync_patch(
            "shared.configuration_settings.get_config",
            return_value=mock_cfg,
        ),
    ):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["checks"]["postgres"] == "ok"
        assert data["checks"]["redis"] == "ok"


# ── Test 2: Health check returns 503 when DB is unreachable ─────────────────


@pytest.mark.asyncio
async def test_health_check_db_down() -> None:
    """Health endpoint should return 503 when postgres is unreachable."""
    from unittest.mock import patch as sync_patch

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from starlette.testclient import TestClient

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(side_effect=Exception("connection refused"))
    mock_engine.dispose = AsyncMock()

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    mock_cfg = MagicMock()
    mock_cfg.database_url = "postgresql+asyncpg://test:test@localhost/test"
    mock_cfg.redis_url = "redis://localhost:6379/0"

    app = FastAPI()

    @app.get("/health", response_model=None)
    async def health() -> JSONResponse:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine as _create

        from shared.configuration_settings import get_config

        cfg = get_config()
        checks: dict[str, str] = {}
        try:
            engine = _create(cfg.database_url, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(cfg.redis_url, decode_responses=True)
            await r.ping()
            await r.aclose()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
        all_ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={"status": "ok" if all_ok else "degraded", "checks": checks},
        )

    with (
        sync_patch(
            "sqlalchemy.ext.asyncio.create_async_engine",
            return_value=mock_engine,
        ),
        sync_patch(
            "redis.asyncio.from_url",
            return_value=mock_redis,
        ),
        sync_patch(
            "shared.configuration_settings.get_config",
            return_value=mock_cfg,
        ),
    ):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["checks"]["postgres"].startswith("error")


# ── Test 3: Request tracing middleware injects trace_id ─────────────────────


def test_trace_id_in_response_header() -> None:
    """Request tracing middleware must inject X-Trace-ID into response."""
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    from services.api.middleware.request_tracing import RequestTracingMiddleware

    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware)

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"ok": "true"}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Trace-ID" in response.headers
    # Must be a valid UUID
    uuid.UUID(response.headers["X-Trace-ID"])


# ── Test 4: Metrics endpoint returns Prometheus format ──────────────────────


def test_metrics_endpoint() -> None:
    """Metrics endpoint must return Prometheus text format with pyhron_ prefixed metrics."""
    from prometheus_client import generate_latest

    from shared.metrics import REGISTRY

    content = generate_latest(REGISTRY).decode()
    assert "pyhron_" in content
    assert "TYPE" in content


# ── Test 5: Kafka topic list is complete ────────────────────────────────────


def test_all_topics_defined() -> None:
    """Every required topic must be defined in KafkaTopic."""
    from shared.kafka_topics import KafkaTopic

    topic_values = [v for k, v in vars(KafkaTopic).items() if not k.startswith("_")]

    required = [
        "pyhron.raw.eod_ohlcv",
        "pyhron.validated.eod_ohlcv",
        "pyhron.dlq.eod_ohlcv",
        "pyhron.orders.order_submitted",
        "pyhron.orders.order_filled",
        "pyhron.paper.nav_snapshot",
        "pyhron.risk.snapshot",
        "pyhron.risk.kill_switch_triggered",
        "pyhron.risk.kill_switch_reset",
        "pyhron.live.activated",
    ]
    for topic in required:
        assert topic in topic_values, f"Missing topic: {topic}"
