"""Unit tests for services.api.logging — ELKJSONRenderer, RequestLoggingMiddleware, AuditLogMiddleware."""

from __future__ import annotations

import json

import pytest

from services.api.logging import (
    AuditLogMiddleware,
    ELKJSONRenderer,
    RequestLoggingMiddleware,
    configure_logging,
)

# ELKJSONRenderer


class TestELKJSONRenderer:
    def test_produces_valid_json(self) -> None:
        renderer = ELKJSONRenderer(service_name="test-svc")
        result = renderer(
            logger_obj=None,
            name="info",
            event_dict={"event": "hello", "level": "INFO"},
        )
        parsed = json.loads(result)
        assert parsed["message"] == "hello"
        assert parsed["level"] == "INFO"
        assert parsed["service"] == "test-svc"
        assert "@timestamp" in parsed

    def test_default_service_name(self) -> None:
        renderer = ELKJSONRenderer()
        result = renderer(None, "info", {"event": "test", "level": "INFO"})
        parsed = json.loads(result)
        assert parsed["service"] == "pyhron"

    def test_extra_fields_included(self) -> None:
        renderer = ELKJSONRenderer()
        result = renderer(None, "info", {"event": "req", "level": "INFO", "path": "/health", "duration_ms": 5.2})
        parsed = json.loads(result)
        assert parsed["path"] == "/health"
        assert parsed["duration_ms"] == 5.2


# configure_logging


def test_configure_logging_json_mode() -> None:
    configure_logging(level="WARNING", json_output=True, service_name="test")
    # Should not raise


def test_configure_logging_console_mode() -> None:
    configure_logging(level="DEBUG", json_output=False)
    # Should not raise


# RequestLoggingMiddleware


@pytest.mark.asyncio
async def test_request_logging_middleware_logs_http() -> None:
    """Middleware logs HTTP requests and passes through."""
    response_started = False

    async def mock_app(scope, receive, send):
        nonlocal response_started
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})
        response_started = True

    middleware = RequestLoggingMiddleware(mock_app, service_name="test")

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "query_string": b"",
        "headers": [],
        "root_path": "",
        "server": ("localhost", 8000),
    }

    messages: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        messages.append(message)

    await middleware(scope, receive, send)
    assert response_started
    assert any(m.get("status") == 200 for m in messages)


@pytest.mark.asyncio
async def test_request_logging_middleware_skips_non_http() -> None:
    """Middleware passes non-HTTP scopes through unchanged."""
    called = False

    async def mock_app(scope, receive, send):
        nonlocal called
        called = True

    middleware = RequestLoggingMiddleware(mock_app)
    await middleware({"type": "websocket"}, None, None)
    assert called


# AuditLogMiddleware


@pytest.mark.asyncio
async def test_audit_log_middleware_skips_get() -> None:
    """Audit middleware does not log GET requests."""
    called = False

    async def mock_app(scope, receive, send):
        nonlocal called
        called = True
        await send({"type": "http.response.start", "status": 200, "headers": []})

    middleware = AuditLogMiddleware(mock_app)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/orders",
        "query_string": b"",
        "headers": [],
        "root_path": "",
        "server": ("localhost", 8000),
    }

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        pass

    await middleware(scope, receive, send)
    assert called


@pytest.mark.asyncio
async def test_audit_log_middleware_logs_post() -> None:
    """Audit middleware logs POST requests."""

    async def mock_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 201, "headers": []})

    middleware = AuditLogMiddleware(mock_app)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/orders",
        "query_string": b"",
        "headers": [],
        "root_path": "",
        "server": ("localhost", 8000),
    }

    async def receive():
        return {"type": "http.request", "body": b""}

    sent: list[dict] = []

    async def send(message):
        sent.append(message)

    await middleware(scope, receive, send)
    assert any(m.get("status") == 201 for m in sent)
