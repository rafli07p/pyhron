"""Admin / user management endpoints."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from services.api.rest_gateway.auth import TokenPayload, get_current_user
from services.api.rest_gateway.models import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from services.api.rest_gateway.rate_limit import limiter
from services.api.rest_gateway.rbac import Role, require_role

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter(tags=["admin"])
API_VERSION = "v1"


@router.post(f"/api/{API_VERSION}/admin/users", response_model=UserResponse, status_code=201)
@limiter.limit("10/minute")
@require_role(Role.ADMIN)
async def create_user(
    request: Request,
    body: UserCreateRequest,
    user: TokenPayload = Depends(get_current_user),
) -> UserResponse:
    """Create a new user within the authenticated tenant."""
    logger.info("user_created", username=body.username, tenant_id=user.tenant_id)
    return UserResponse(
        username=body.username,
        email=body.email,
        role=body.role,
        tenant_id=user.tenant_id,
    )


@router.get(f"/api/{API_VERSION}/admin/users", response_model=list[UserResponse])
@limiter.limit("30/minute")
@require_role(Role.ADMIN)
async def list_users(
    request: Request,
    user: TokenPayload = Depends(get_current_user),
) -> list[UserResponse]:
    """List all users for the authenticated tenant."""
    return []


@router.get(f"/api/{API_VERSION}/admin/users/{{user_id}}", response_model=UserResponse)
@limiter.limit("30/minute")
@require_role(Role.ADMIN)
async def get_user(
    request: Request,
    user_id: UUID,
    user: TokenPayload = Depends(get_current_user),
) -> UserResponse:
    """Get a specific user by ID."""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.put(f"/api/{API_VERSION}/admin/users/{{user_id}}", response_model=UserResponse)
@limiter.limit("10/minute")
@require_role(Role.ADMIN)
async def update_user(
    request: Request,
    user_id: UUID,
    body: UserUpdateRequest,
    user: TokenPayload = Depends(get_current_user),
) -> UserResponse:
    """Update user details (email, role)."""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.delete(f"/api/{API_VERSION}/admin/users/{{user_id}}", status_code=204, response_model=None)
@limiter.limit("10/minute")
@require_role(Role.ADMIN)
async def delete_user(
    request: Request,
    user_id: UUID,
    user: TokenPayload = Depends(get_current_user),
) -> None:
    """Delete a user from the tenant."""
    logger.info("user_deleted", user_id=str(user_id), tenant_id=user.tenant_id)
