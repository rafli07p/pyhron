"""Role-based access control for the Pyhron REST gateway."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar, cast

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from services.api.rest_gateway.auth import TokenPayload


class Role(StrEnum):
    VIEWER = "viewer"
    TRADER = "trader"
    RESEARCHER = "researcher"
    ADMIN = "admin"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.TRADER: 1,
    Role.RESEARCHER: 2,
    Role.ADMIN: 3,
}


_F = TypeVar("_F", bound=Callable[..., Any])


def require_role(minimum_role: Role) -> Callable[[_F], _F]:
    """Decorator that enforces a minimum RBAC role on an endpoint."""

    def decorator(func: _F) -> _F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user: TokenPayload | None = kwargs.get("user")
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
            if ROLE_HIERARCHY.get(user.role, -1) < ROLE_HIERARCHY[minimum_role]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{user.role}' insufficient; requires '{minimum_role}' or above",
                )
            return await func(*args, **kwargs)

        return cast(_F, wrapper)

    return decorator
