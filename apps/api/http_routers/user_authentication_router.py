"""User authentication API endpoints.

JWT-based authentication with access and refresh tokens,
user registration, and profile management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from shared.security.auth import (
    TokenError,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/auth", tags=["authentication"])
_limiter = Limiter(key_func=get_remote_address)


# ── In-memory user store (swap for database in production) ───────────────────

_users_db: dict[str, dict[str, Any]] = {}


# ── Request/Response Models ──────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=100)
    tenant_id: str = Field(default="default")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900, description="Token TTL in seconds")


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    email: str
    full_name: str
    is_active: bool = True
    role: str = "VIEWER"
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
@_limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest) -> TokenResponse:
    """Authenticate user and return JWT access + refresh tokens."""
    logger.info("login_attempt", email=body.email)

    user = _users_db.get(body.email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        user_id=str(user["id"]),
        tenant_id=user["tenant_id"],
        role=user["role"],
    )
    refresh_tok = create_refresh_token(
        user_id=str(user["id"]),
        tenant_id=user["tenant_id"],
    )

    logger.info("login_success", email=body.email, user_id=str(user["id"]))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_tok,
    )


@router.post("/register", response_model=UserProfileResponse, status_code=201)
@_limiter.limit("3/minute")
async def register(request: Request, body: RegisterRequest) -> UserProfileResponse:
    """Register a new user account."""
    if body.email in _users_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user_id = uuid4()
    _users_db[body.email] = {
        "id": user_id,
        "email": body.email,
        "full_name": body.full_name,
        "hashed_password": hash_password(body.password),
        "role": Role.VIEWER.value,
        "tenant_id": body.tenant_id,
        "is_active": True,
        "created_at": datetime.now(tz=UTC),
    }

    logger.info("user_registered", email=body.email, user_id=str(user_id))
    return UserProfileResponse(
        id=user_id,
        email=body.email,
        full_name=body.full_name,
        tenant_id=body.tenant_id,
    )


@router.post("/refresh", response_model=TokenResponse)
@_limiter.limit("10/minute")
async def refresh_token(request: Request, body: RefreshRequest) -> TokenResponse:
    """Refresh an expired access token using a valid refresh token."""
    try:
        payload = verify_token(body.refresh_token)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.raw.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )

    # Find user to get current role
    user = None
    for u in _users_db.values():
        if str(u["id"]) == payload.sub:
            user = u
            break

    role = user["role"] if user else "VIEWER"
    access_token = create_access_token(
        user_id=payload.sub,
        tenant_id=payload.tenant_id,
        role=role,
    )
    new_refresh = create_refresh_token(
        user_id=payload.sub,
        tenant_id=payload.tenant_id,
    )

    logger.info("token_refreshed", user_id=payload.sub)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user(
    user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> UserProfileResponse:
    """Get the authenticated user's profile."""
    for u in _users_db.values():
        if str(u["id"]) == user.sub:
            return UserProfileResponse(
                id=u["id"],
                email=u["email"],
                full_name=u["full_name"],
                is_active=u["is_active"],
                role=u["role"],
                tenant_id=u["tenant_id"],
                created_at=u["created_at"],
            )

    return UserProfileResponse(
        id=UUID(user.sub) if user.sub else uuid4(),
        email="unknown",
        full_name="Unknown User",
        role=user.role,
        tenant_id=user.tenant_id,
    )
