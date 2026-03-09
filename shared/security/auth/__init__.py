"""JWT authentication utilities for the Enthropy platform.

Provides token creation, verification, and password hashing using
:pypi:`PyJWT` and :pypi:`passlib`.  Designed to be used as FastAPI
dependencies or standalone helper functions.

Usage::

    from shared.security.auth import create_access_token, verify_token

    token = create_access_token(user_id="u-123", tenant_id="t-acme", role="TRADER")
    payload = verify_token(token)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from shared.configuration_settings import get_config as get_settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        password: Plain-text password.

    Returns:
        Bcrypt hash string.
    """
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash.

    Args:
        plain_password: Plain-text password to check.
        hashed_password: Stored bcrypt hash.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT token management
# ---------------------------------------------------------------------------


class TokenError(Exception):
    """Raised when a JWT cannot be created or verified."""


class TokenPayload:
    """Decoded JWT payload with typed accessors.

    Attributes:
        sub: Subject (user ID).
        tenant_id: Tenant identifier.
        role: User role name.
        exp: Expiry timestamp.
        iat: Issued-at timestamp.
        jti: Unique token identifier.
        scopes: Optional list of granted scopes.
        raw: Full decoded payload dict.
    """

    __slots__ = ("exp", "iat", "jti", "raw", "role", "scopes", "sub", "tenant_id")

    def __init__(self, payload: dict[str, Any]) -> None:
        self.raw = payload
        self.sub: str = payload.get("sub", "")
        self.tenant_id: str = payload.get("tenant_id", "")
        self.role: str = payload.get("role", "")
        self.exp: datetime | None = None
        self.iat: datetime | None = None
        self.jti: str | None = payload.get("jti")
        self.scopes: list[str] = payload.get("scopes", [])

        if "exp" in payload:
            self.exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        if "iat" in payload:
            self.iat = datetime.fromtimestamp(payload["iat"], tz=UTC)

    def __repr__(self) -> str:
        return f"TokenPayload(sub={self.sub!r}, tenant_id={self.tenant_id!r}, role={self.role!r})"

    @property
    def is_expired(self) -> bool:
        """Return ``True`` if the token has expired."""
        if self.exp is None:
            return False
        return datetime.now(tz=UTC) >= self.exp


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str = "VIEWER",
    *,
    scopes: list[str] | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        user_id: User identifier (becomes the ``sub`` claim).
        tenant_id: Tenant identifier for multi-tenancy.
        role: User role (e.g. ``ADMIN``, ``TRADER``).
        scopes: Optional list of granted scopes.
        expires_delta: Custom expiry duration.  Defaults to the value
            configured in :class:`~shared.configuration_settings.Config`.
        extra_claims: Additional claims to include in the token payload.

    Returns:
        Encoded JWT string.

    Raises:
        TokenError: If token creation fails.
    """
    settings = get_settings()
    now = datetime.now(tz=UTC)

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "scopes": scopes or [],
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.app_name,
    }

    if extra_claims:
        payload.update(extra_claims)

    try:
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    except Exception as exc:
        raise TokenError(f"Failed to create access token: {exc}") from exc


def create_refresh_token(
    user_id: str,
    tenant_id: str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token.

    Refresh tokens carry minimal claims and have a longer TTL.

    Args:
        user_id: User identifier.
        tenant_id: Tenant identifier.
        expires_delta: Custom expiry duration.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(tz=UTC)

    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "type": "refresh",
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.app_name,
    }

    try:
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    except Exception as exc:
        raise TokenError(f"Failed to create refresh token: {exc}") from exc


def verify_token(token: str, *, verify_exp: bool = True) -> TokenPayload:
    """Decode and verify a JWT token.

    Args:
        token: Encoded JWT string.
        verify_exp: Whether to verify the expiration claim.

    Returns:
        Decoded :class:`TokenPayload`.

    Raises:
        TokenError: If the token is invalid, expired, or tampered.
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": verify_exp},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc

    if not payload.get("sub"):
        raise TokenError("Token is missing 'sub' claim")
    if not payload.get("tenant_id"):
        raise TokenError("Token is missing 'tenant_id' claim")

    return TokenPayload(payload)


__all__ = [
    "TokenError",
    "TokenPayload",
    "create_access_token",
    "create_refresh_token",
    "hash_password",
    "verify_password",
    "verify_token",
]
