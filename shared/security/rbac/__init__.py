"""Role-Based Access Control (RBAC) for the Pyhron platform.

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
from typing import TYPE_CHECKING, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.security.auth import TokenPayload, verify_token

if TYPE_CHECKING:
    from collections.abc import Callable

# Enumerations

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


# Role hierarchy (higher number = more privileges)

ROLE_HIERARCHY: dict[Role, int] = {
    Role.ADMIN: 4,
    Role.TRADER: 3,
    Role.ANALYST: 2,
    Role.VIEWER: 1,
}


# Role -> Permission mapping

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


# Permission checks

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
    """FastAPI dependency — user must have AT LEAST the minimum role.

    When called with a single role, accepts that role AND all higher roles.
    When called with multiple roles, the lowest of the supplied roles
    becomes the effective minimum (so any role at or above that level passes).

    Examples:
        require_role(Role.VIEWER)  -> VIEWER, ANALYST, TRADER, ADMIN all pass
        require_role(Role.TRADER)  -> TRADER, ADMIN pass; ANALYST, VIEWER fail
        require_role(Role.ADMIN)   -> only ADMIN passes
    """
    min_level = min(ROLE_HIERARCHY.get(r, 0) for r in roles)

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

        try:
            user_role = Role(payload.role)
        except ValueError:
            user_role = None
        user_level = ROLE_HIERARCHY.get(user_role, 0) if user_role else 0

        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient role. Required minimum: "
                    f"{[r.value for r in roles]}. Got '{payload.role}'."
                ),
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
    "ROLE_HIERARCHY",
    "ROLE_PERMISSIONS",
    "Permission",
    "Role",
    "check_permission",
    "require_permission",
    "require_role",
    "require_tenant",
]
