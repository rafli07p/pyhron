"""JWT authentication for the Pyhron REST gateway."""

from __future__ import annotations

import jwt
import structlog
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from services.api.rest_gateway.rbac import Role
from shared.configuration_settings import get_config as _get_settings

logger = structlog.stdlib.get_logger(__name__)


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: Role = Role.VIEWER
    exp: int | None = None


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
