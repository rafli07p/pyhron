"""Role-Based Access Control (RBAC) for the Enthropy platform.

Provides role and permission enumerations, a ``require_role`` FastAPI
dependency, and a ``check_permission`` helper for imperative checks.

Usage in FastAPI::

    from shared.security.rbac import require_role, Role

    @router.post("/orders")
    async def create_order(
        payload: OrderRequest,
        user: TokenPayload = Depends(require_role(Role.TRADER)),
    ):
        ...

Standalone usage::

    from shared.security.rbac import check_permission, Role, Permission

    check_permission(role=Role.ANALYST, permission=Permission.READ_PORTFOLIO)
"""

from __future__ import annotations

from enum import StrEnum, unique
from functools import wraps
from typing import Any, Callable, Sequence

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.security.auth import TokenPayload, verify_token

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=True)


@unique
class Role(StrEnum):
    """Platform roles ordered by privilege level (highest first)."""

    ADMIN = "ADMIN"
    TRADER = "TRADER"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


@unique
class Permission(StrEnum):
    """Granular permissions for resource-level access control."""

    # Orders
    CREATE_ORDER = "CREATE_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    VIEW_ORDERS = "VIEW_ORDERS"

    # Portfolio
    READ_PORTFOLIO = "READ_PORTFOLIO"
    MODIFY_PORTFOLIO = "MODIFY_PORTFOLIO"

    # Market data
    READ_MARKET_DATA = "READ_MARKET_DATA"
    SUBSCRIBE_MARKET_DATA = "SUBSCRIBE_MARKET_DATA"

    # Research
    RUN_BACKTEST = "RUN_BACKTEST"
    VIEW_RESEARCH = "VIEW_RESEARCH"

    # Risk
    VIEW_RISK = "VIEW_RISK"
    MODIFY_RISK_LIMITS = "MODIFY_RISK_LIMITS"

    # Administration
    MANAGE_USERS = "MANAGE_USERS"
    MANAGE_TENANTS = "MANAGE_TENANTS"
    VIEW_AUDIT_LOG = "VIEW_AUDIT_LOG"
    MANAGE_CONFIG = "MANAGE_CONFIG"


# ---------------------------------------------------------------------------
# Role -> Permission mapping
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),  # Admin gets everything
    Role.TRADER: frozenset({
        Permission.CREATE_ORDER,
        Permission.CANCEL_ORDER,
        Permission.VIEW_ORDERS,
        Permission.READ_PORTFOLIO,
        Permission.MODIFY_PORTFOLIO,
        Permission.READ_MARKET_DATA,
        Permission.SUBSCRIBE_MARKET_DATA,
        Permission.RUN_BACKTEST,
        Permission.VIEW_RESEARCH,
        Permission.VIEW_RISK,
    }),
    Role.ANALYST: frozenset({
        Permission.VIEW_ORDERS,
        Permission.READ_PORTFOLIO,
        Permission.READ_MARKET_DATA,
        Permission.SUBSCRIBE_MARKET_DATA,
        Permission.RUN_BACKTEST,
        Permission.VIEW_RESEARCH,
        Permission.VIEW_RISK,
    }),
    Role.VIEWER: frozenset({
        Permission.VIEW_ORDERS,
        Permission.READ_PORTFOLIO,
        Permission.READ_MARKET_DATA,
        Permission.VIEW_RESEARCH,
        Permission.VIEW_RISK,
    }),
}


# ---------------------------------------------------------------------------
# Permission checks
# ---------------------------------------------------------------------------

def check_permission(role: Role | str, permission: Permission) -> bool:
    """Check whether *role* has *permission*.

    Args:
        role: The user's role (a :class:`Role` enum or its string value).
        permission: The required permission.

    Returns:
        ``True`` if the role grants the permission, ``False`` otherwise.
    """
    if isinstance(role, str):
        try:
            role = Role(role)
        except ValueError:
            return False

    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def require_permission(permission: Permission) -> Callable[..., Any]:
    """FastAPI dependency that verifies the caller has *permission*.

    Extracts the JWT from the ``Authorization`` header, decodes it,
    and checks the user's role against the permission matrix.

    Raises:
        HTTPException: 401 if the token is invalid; 403 if the
            caller lacks the required permission.
    """

    async def _dependency(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    ) -> TokenPayload:
        from shared.security.auth import TokenError

        try:
            payload = verify_token(credentials.credentials)
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if not check_permission(payload.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' is required. Your role '{payload.role}' does not have it.",
            )

        return payload

    return _dependency


def require_role(*roles: Role) -> Callable[..., Any]:
    """FastAPI dependency that restricts access to specific roles.

    Accepts one or more :class:`Role` values.  The caller's JWT is
    extracted, decoded, and its role is checked against the allowed
    list.

    Args:
        roles: One or more allowed roles.

    Returns:
        FastAPI dependency function that yields a :class:`TokenPayload`.

    Example::

        @router.get("/admin/users")
        async def list_users(
            user: TokenPayload = Depends(require_role(Role.ADMIN)),
        ):
            ...
    """
    allowed: frozenset[str] = frozenset(r.value for r in roles)

    async def _dependency(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    ) -> TokenPayload:
        from shared.security.auth import TokenError

        try:
            payload = verify_token(credentials.credentials)
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if payload.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role must be one of {sorted(allowed)}. Got '{payload.role}'.",
            )

        return payload

    return _dependency


def require_tenant(tenant_id: str) -> Callable[..., Any]:
    """FastAPI dependency that ensures the caller belongs to *tenant_id*.

    Useful for tenant-scoped endpoints where the tenant is part of
    the URL path.

    Args:
        tenant_id: Required tenant identifier.
    """

    async def _dependency(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    ) -> TokenPayload:
        from shared.security.auth import TokenError

        try:
            payload = verify_token(credentials.credentials)
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if payload.role != Role.ADMIN and payload.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant mismatch.",
            )

        return payload

    return _dependency


__all__ = [
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    "check_permission",
    "require_permission",
    "require_role",
    "require_tenant",
]
