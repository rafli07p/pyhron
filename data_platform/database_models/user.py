"""User account model.

Stores authentication credentials, role-based access, and brute-force
lockout state for platform users.
"""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.async_database_session import Base

if TYPE_CHECKING:
    from datetime import datetime


class UserRole(enum.StrEnum):
    """Platform user roles."""

    ADMIN = "admin"
    TRADER = "trader"
    ANALYST = "analyst"
    READONLY = "readonly"


class User(Base):
    """Platform user account.

    Attributes:
        id: UUID primary key.
        email: Unique email address.
        hashed_password: bcrypt/argon2 hash — never plaintext.
        role: Role-based access level.
        is_active: Whether the account is enabled.
        is_verified: Whether email has been verified.
        failed_login_attempts: Counter for brute-force lockout.
        locked_until: Lockout expiry timestamp.
        last_login_at: Most recent successful login.
        created_at: Row creation timestamp.
        updated_at: Row last-update timestamp.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        ENUM(UserRole, name="user_role", create_type=False),
        nullable=False,
        default=UserRole.READONLY,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
