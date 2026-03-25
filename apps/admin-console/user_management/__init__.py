"""User management with RBAC and multi-tenancy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog

from shared.security.auth import hash_password, verify_password
from shared.security.rbac import Role

logger = structlog.get_logger(__name__)


@dataclass
class User:
    user_id: UUID
    username: str
    email: str
    hashed_password: str
    role: Role
    tenant_id: str
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    last_login: datetime | None = None


class UserManager:
    """CRUD operations for users with RBAC and multi-tenancy."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: Role,
        tenant_id: str,
    ) -> User:
        user = User(
            user_id=uuid4(),
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=role,
            tenant_id=tenant_id,
        )
        self._users[user.user_id] = user
        logger.info(
            "user_created",
            user_id=str(user.user_id),
            username=username,
            role=role,
            tenant_id=tenant_id,
        )
        return user

    async def update_user(
        self, user_id: UUID, tenant_id: str, **updates: object
    ) -> User:
        user = self._get(user_id, tenant_id)
        for k, v in updates.items():
            if k == "password":
                user.hashed_password = hash_password(str(v))
            elif hasattr(user, k):
                setattr(user, k, v)
        logger.info("user_updated", user_id=str(user_id), tenant_id=tenant_id)
        return user

    async def delete_user(self, user_id: UUID, tenant_id: str) -> None:
        user = self._get(user_id, tenant_id)
        user.is_active = False
        logger.info("user_deactivated", user_id=str(user_id), tenant_id=tenant_id)

    async def assign_role(self, user_id: UUID, role: Role, tenant_id: str) -> User:
        user = self._get(user_id, tenant_id)
        user.role = role
        logger.info("role_assigned", user_id=str(user_id), role=role)
        return user

    async def authenticate(
        self, username: str, password: str, tenant_id: str
    ) -> User | None:
        for user in self._users.values():
            if (
                user.username == username
                and user.tenant_id == tenant_id
                and user.is_active
                and verify_password(password, user.hashed_password)
            ):
                user.last_login = datetime.now(tz=UTC)
                return user
        return None

    async def list_users(self, tenant_id: str) -> list[User]:
        return [u for u in self._users.values() if u.tenant_id == tenant_id]

    def _get(self, user_id: UUID, tenant_id: str) -> User:
        user = self._users.get(user_id)
        if user is None or user.tenant_id != tenant_id:
            raise KeyError(f"User {user_id} not found for tenant {tenant_id}")
        return user
