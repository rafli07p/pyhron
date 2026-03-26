"""Unit tests for REST gateway middlewares — CSRF, SecurityHeaders, RequestID."""

from __future__ import annotations

import pytest

from services.api.rest_gateway import (
    CSRFMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

# Helpers


def _make_scope(
    method: str = "GET",
    path: str = "/v1/orders",
    headers: list[tuple[bytes, bytes]] | None = None,
    cookies: str = "",
) -> dict:
    hdrs = list(headers or [])
    if cookies:
        hdrs.append((b"cookie", cookies.encode()))
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": hdrs,
        "root_path": "",
        "server": ("localhost", 8000),
    }


# SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    @pytest.mark.asyncio
    async def test_adds_security_headers(self) -> None:
        final_headers: list[tuple[bytes, bytes]] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})

        middleware = SecurityHeadersMiddleware(mock_app)

        async def capture_send(message):
            if message["type"] == "http.response.start":
                final_headers.extend(message.get("headers", []))

        await middleware(_make_scope(), None, capture_send)

        header_names = {h[0] for h in final_headers}
        assert b"x-content-type-options" in header_names
        assert b"x-frame-options" in header_names
        assert b"strict-transport-security" in header_names
        assert b"referrer-policy" in header_names
        assert b"content-security-policy" in header_names

    @pytest.mark.asyncio
    async def test_skips_non_http(self) -> None:
        called = False

        async def mock_app(scope, receive, send):
            nonlocal called
            called = True

        middleware = SecurityHeadersMiddleware(mock_app)
        await middleware({"type": "websocket"}, None, None)
        assert called


# CSRFMiddleware


class TestCSRFMiddleware:
    @pytest.mark.asyncio
    async def test_get_sets_csrf_cookie(self) -> None:
        set_cookie_found = False

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})

        middleware = CSRFMiddleware(mock_app)

        async def capture_send(message):
            nonlocal set_cookie_found
            if message["type"] == "http.response.start":
                for name, value in message.get("headers", []):
                    if name == b"set-cookie" and b"csrf_token=" in value:
                        set_cookie_found = True

        await middleware(
            _make_scope(method="GET"),
            lambda: {"type": "http.request", "body": b""},
            capture_send,
        )
        assert set_cookie_found

    @pytest.mark.asyncio
    async def test_post_without_csrf_returns_403(self) -> None:
        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})

        middleware = CSRFMiddleware(mock_app)
        responses: list[dict] = []

        async def capture_send(message):
            responses.append(message)

        async def receive():
            return {"type": "http.request", "body": b""}

        await middleware(
            _make_scope(method="POST", path="/v1/orders"),
            receive,
            capture_send,
        )
        # Should get 403 CSRF rejection
        assert any(m.get("status") == 403 for m in responses)

    @pytest.mark.asyncio
    async def test_post_with_matching_csrf_passes(self) -> None:
        """POST with matching cookie + header passes CSRF check."""
        token = "test-csrf-token-value"  # noqa: S105
        app_called = False

        async def mock_app(scope, receive, send):
            nonlocal app_called
            app_called = True
            await send({"type": "http.response.start", "status": 201, "headers": []})

        middleware = CSRFMiddleware(mock_app)

        async def receive():
            return {"type": "http.request", "body": b""}

        sent: list[dict] = []

        async def send(message):
            sent.append(message)

        scope = _make_scope(
            method="POST",
            path="/v1/orders",
            headers=[(b"x-csrf-token", token.encode())],
            cookies=f"csrf_token={token}",
        )
        await middleware(scope, receive, send)
        assert app_called

    @pytest.mark.asyncio
    async def test_auth_endpoints_exempt_from_csrf(self) -> None:
        """Auth endpoints are CSRF-exempt."""
        app_called = False

        async def mock_app(scope, receive, send):
            nonlocal app_called
            app_called = True
            await send({"type": "http.response.start", "status": 200, "headers": []})

        middleware = CSRFMiddleware(mock_app)

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        await middleware(
            _make_scope(method="POST", path="/v1/auth/login"),
            receive,
            send,
        )
        assert app_called


# RequestIDMiddleware


class TestRequestIDMiddleware:
    @pytest.mark.asyncio
    async def test_generates_request_id(self) -> None:
        response_headers: list[tuple[bytes, bytes]] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})

        middleware = RequestIDMiddleware(mock_app)

        async def capture_send(message):
            if message["type"] == "http.response.start":
                response_headers.extend(message.get("headers", []))

        await middleware(
            _make_scope(),
            lambda: {"type": "http.request", "body": b""},
            capture_send,
        )
        header_dict = dict(response_headers)
        assert b"x-request-id" in header_dict
        assert len(header_dict[b"x-request-id"]) > 0

    @pytest.mark.asyncio
    async def test_propagates_existing_request_id(self) -> None:
        response_headers: list[tuple[bytes, bytes]] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})

        middleware = RequestIDMiddleware(mock_app)

        async def capture_send(message):
            if message["type"] == "http.response.start":
                response_headers.extend(message.get("headers", []))

        scope = _make_scope(headers=[(b"x-request-id", b"req-123")])
        await middleware(
            scope,
            lambda: {"type": "http.request", "body": b""},
            capture_send,
        )
        header_dict = dict(response_headers)
        assert header_dict[b"x-request-id"] == b"req-123"
