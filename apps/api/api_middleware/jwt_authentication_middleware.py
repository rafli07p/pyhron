"""JWT authentication middleware.

Validates JWT access tokens on incoming requests, extracts user claims,
and injects the authenticated user into the request state.
Skips validation for public/health endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from shared.configuration_settings import get_config
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────


def _get_jwt_secret() -> str:
    return get_config().jwt_secret_key


def _get_jwt_algorithm() -> str:
    return get_config().jwt_algorithm


PUBLIC_PATHS: set[str] = {
    "/v1/auth/login",
    "/v1/auth/register",
    "/v1/auth/refresh",
    "/health",
    "/readiness",
    "/docs",
    "/openapi.json",
}


# ── Helper ───────────────────────────────────────────────────────────────────


def _decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token, returning the payload claims."""
    return jwt.decode(token, _get_jwt_secret(), algorithms=[_get_jwt_algorithm()])


def _is_public_path(path: str) -> bool:
    """Check whether the request path is exempt from authentication."""
    return path in PUBLIC_PATHS or path.startswith("/v1/auth/")


# ── Middleware ───────────────────────────────────────────────────────────────


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that validates JWT Bearer tokens."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if _is_public_path(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("auth_missing", path=request.url.path)
            return Response(
                content='{"detail":"Missing or invalid Authorization header"}',
                status_code=401,
                media_type="application/json",
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            claims = _decode_token(token)
            request.state.user_id = claims.get("sub")
            request.state.user_claims = claims
        except JWTError as exc:
            logger.warning("auth_invalid_token", error=str(exc), path=request.url.path)
            return Response(
                content='{"detail":"Invalid or expired token"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
