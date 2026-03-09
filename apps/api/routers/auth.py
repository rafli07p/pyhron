"""Authentication API endpoints.

JWT-based authentication with access and refresh tokens.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/auth", tags=["auth"])


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
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool = True
    created_at: datetime


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """Authenticate user and return JWT tokens."""
    # In production: verify credentials against DB, issue JWT
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest) -> UserResponse:
    """Register a new user account."""
    # In production: hash password, create user in DB
    logger.info("user_registered", email=body.email)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Registration not yet implemented",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest) -> TokenResponse:
    """Refresh an expired access token."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user() -> UserResponse:
    """Get current authenticated user profile."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
