"""ASGI middlewares for the Pyhron REST gateway."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


# CSRF protection (double-submit cookie)

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


# Security headers

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


# Request-ID propagation


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
