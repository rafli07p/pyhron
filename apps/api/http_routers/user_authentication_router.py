"""User authentication API endpoints.

JWT-based authentication with access and refresh tokens,
user registration, and profile management.
Uses database-backed user storage with brute-force lockout protection.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from data_platform.database_models.user import User, UserRole
from shared.async_database_session import get_session
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

# Lockout configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Role mapping: DB UserRole -> JWT Role string
_ROLE_MAP: dict[UserRole, str] = {
    UserRole.ADMIN: Role.ADMIN.value,
    UserRole.TRADER: Role.TRADER.value,
    UserRole.ANALYST: Role.ANALYST.value,
    UserRole.READONLY: Role.VIEWER.value,
}


# Request/Response Models
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
    token_type: str = "bearer"  # noqa: S105 — OAuth2 standard field, not a password
    expires_in: int = Field(default=900, description="Token TTL in seconds")


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool = True
    role: str = "VIEWER"
    tenant_id: str = "default"
    created_at: datetime


# Endpoints
@router.post("/login", response_model=TokenResponse)
@_limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest) -> TokenResponse:
    """Authenticate user and return JWT access + refresh tokens."""
    logger.info("login_attempt", email=body.email)

    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check lockout
        if user.locked_until and user.locked_until > datetime.now(tz=UTC):
            logger.warning("login_locked_out", email=body.email)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed attempts",
            )

        # Check active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        # Verify password
        if not verify_password(body.password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.now(tz=UTC) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                logger.warning("account_locked", email=body.email, attempts=user.failed_login_attempts)
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Successful login: reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(tz=UTC)
        await session.commit()

    jwt_role = _ROLE_MAP.get(user.role, Role.VIEWER.value)
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id="default",
        role=jwt_role,
    )
    refresh_tok = create_refresh_token(
        user_id=str(user.id),
        tenant_id="default",
    )

    logger.info("login_success", email=body.email, user_id=str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_tok,
    )


@router.post("/register", response_model=UserProfileResponse, status_code=201)
@_limiter.limit("3/minute")
async def register(request: Request, body: RegisterRequest) -> UserProfileResponse:
    """Register a new user account."""
    async with get_session() as session:
        # Check if email already exists
        existing = await session.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = User(
            email=body.email,
            hashed_password=hash_password(body.password),
            role=UserRole.READONLY,
            is_active=True,
            is_verified=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    logger.info("user_registered", email=body.email, user_id=str(user.id))
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=body.full_name,
        tenant_id=body.tenant_id,
        is_active=user.is_active,
        role=_ROLE_MAP.get(user.role, Role.VIEWER.value),
        created_at=user.created_at,
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

    # Look up user in DB for current role
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == UUID(payload.sub)))
        user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    jwt_role = _ROLE_MAP.get(user.role, Role.VIEWER.value)
    access_token = create_access_token(
        user_id=payload.sub,
        tenant_id=payload.tenant_id,
        role=jwt_role,
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
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == UUID(user.sub)))
        db_user = result.scalar_one_or_none()

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserProfileResponse(
        id=db_user.id,
        email=db_user.email,
        full_name=db_user.email.split("@")[0],
        is_active=db_user.is_active,
        role=_ROLE_MAP.get(db_user.role, Role.VIEWER.value),
        tenant_id="default",
        created_at=db_user.created_at,
    )
