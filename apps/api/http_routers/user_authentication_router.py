"""User authentication API endpoints.

JWT-based authentication with access and refresh tokens,
user registration, and profile management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/auth", tags=["authentication"])


# ── Request/Response Models ──────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=3600, description="Token TTL in seconds")


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    email: str
    full_name: str
    is_active: bool = True
    subscription_tier: str = "free"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """Authenticate user and return JWT access + refresh tokens."""
    # In production: verify credentials against DB, issue signed JWT
    logger.info("login_attempt", email=body.email)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )


@router.post("/register", response_model=UserProfileResponse, status_code=201)
async def register(body: RegisterRequest) -> UserProfileResponse:
    """Register a new user account."""
    # In production: hash password, persist user, send verification email
    logger.info("user_registered", email=body.email, full_name=body.full_name)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Registration not yet implemented",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest) -> TokenResponse:
    """Refresh an expired access token using a valid refresh token."""
    # In production: validate refresh token, rotate tokens
    logger.info("token_refresh_attempt")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user() -> UserProfileResponse:
    """Get the authenticated user's profile."""
    # In production: extract user_id from JWT, query user table
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
