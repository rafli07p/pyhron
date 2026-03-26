"""Unit tests for the paper trading consumer health endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.http_routers import paper_trading_router


@pytest.fixture(autouse=True)
def _reset_consumer_instance():
    """Reset the global consumer instance between tests."""
    original = paper_trading_router._consumer_instance
    paper_trading_router._consumer_instance = None
    yield
    paper_trading_router._consumer_instance = original


@pytest.fixture()
def app():
    """Minimal FastAPI app with the paper trading router."""
    from fastapi import FastAPI

    _app = FastAPI()
    _app.include_router(paper_trading_router.router)
    return _app


class TestConsumerHealthEndpoint:
    """Tests for GET /v1/paper-trading/consumer/health."""

    @pytest.mark.asyncio()
    async def test_no_consumer_registered(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/paper-trading/consumer/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_registered"

    @pytest.mark.asyncio()
    async def test_healthy_consumer(self, app):
        mock_consumer = MagicMock()
        from services.paper_trading.strategy_signal_consumer import ConsumerHealthStatus

        mock_consumer.health.return_value = ConsumerHealthStatus(
            running=True,
            started_at=datetime(2025, 1, 15, 9, 0, tzinfo=UTC),
            last_message_at=datetime(2025, 1, 15, 9, 30, tzinfo=UTC),
            messages_processed=100,
            batches_flushed=5,
            errors=2,
            topics=["pyhron.strategy.signals.momentum"],
            consumer_group="paper-strategy-executor",
        )
        paper_trading_router.register_consumer(mock_consumer)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/paper-trading/consumer/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["running"] is True
        assert data["messages_processed"] == 100
        assert data["batches_flushed"] == 5

    @pytest.mark.asyncio()
    async def test_stopped_consumer(self, app):
        mock_consumer = MagicMock()
        from services.paper_trading.strategy_signal_consumer import ConsumerHealthStatus

        mock_consumer.health.return_value = ConsumerHealthStatus(running=False)
        paper_trading_router.register_consumer(mock_consumer)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/paper-trading/consumer/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "stopped"
        assert data["running"] is False


class TestRegisterConsumer:
    """Tests for the register_consumer helper."""

    def test_register_sets_global(self):
        mock = MagicMock()
        paper_trading_router.register_consumer(mock)
        assert paper_trading_router._consumer_instance is mock

    def test_register_none_clears(self):
        paper_trading_router.register_consumer(MagicMock())
        paper_trading_router.register_consumer(None)
        assert paper_trading_router._consumer_instance is None
