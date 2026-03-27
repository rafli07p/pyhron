"""Unit tests for JWT authentication utilities.

Validates token creation, verification, expiry, password hashing,
and error handling for the auth module.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

try:
    from shared.security.auth import (
        TokenError,
        TokenPayload,
        create_access_token,
        create_refresh_token,
        hash_password,
        verify_password,
        verify_token,
    )
except ImportError:
    pytest.skip("Requires shared.security.auth module", allow_module_level=True)


def _mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.jwt_secret_key = "test-secret-key-that-is-long-enough-for-hs256"  # noqa: S105
    settings.jwt_algorithm = "HS256"
    settings.jwt_access_token_expire_minutes = 15
    settings.jwt_refresh_token_expire_days = 7
    settings.app_name = "pyhron-test"
    return settings


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_and_verify(self) -> None:
        """Hashed password should verify correctly."""
        password = "secure_password_123!"  # noqa: S105
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self) -> None:
        """Wrong password should not verify."""
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_not_plaintext(self) -> None:
        """Hash should not contain the original password."""
        password = "my_secret"  # noqa: S105
        hashed = hash_password(password)
        assert password not in hashed

    def test_different_hashes_for_same_password(self) -> None:
        """Same password should produce different hashes (salt)."""
        password = "same_password"  # noqa: S105
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestTokenCreation:
    """Tests for JWT token creation."""

    @patch("shared.security.auth.get_settings")
    def test_create_access_token(self, mock_get: MagicMock) -> None:
        """Access token should be created and decodable."""
        mock_get.return_value = _mock_settings()

        token = create_access_token("user-1", "tenant-1", "TRADER")
        assert isinstance(token, str)
        assert len(token) > 0

        payload = verify_token(token)
        assert payload.sub == "user-1"
        assert payload.tenant_id == "tenant-1"
        assert payload.role == "TRADER"

    @patch("shared.security.auth.get_settings")
    def test_create_token_with_scopes(self, mock_get: MagicMock) -> None:
        """Token should include custom scopes."""
        mock_get.return_value = _mock_settings()

        token = create_access_token("user-1", "tenant-1", scopes=["read", "write"])
        payload = verify_token(token)
        assert "read" in payload.scopes
        assert "write" in payload.scopes

    @patch("shared.security.auth.get_settings")
    def test_create_token_with_extra_claims(self, mock_get: MagicMock) -> None:
        """Extra claims should be included in the token."""
        mock_get.return_value = _mock_settings()

        token = create_access_token("user-1", "tenant-1", extra_claims={"strategy_id": "momentum_v1"})
        payload = verify_token(token)
        assert payload.raw.get("strategy_id") == "momentum_v1"

    @patch("shared.security.auth.get_settings")
    def test_create_refresh_token(self, mock_get: MagicMock) -> None:
        """Refresh token should be created with minimal claims."""
        mock_get.return_value = _mock_settings()

        token = create_refresh_token("user-1", "tenant-1")
        payload = verify_token(token)
        assert payload.sub == "user-1"
        assert payload.raw.get("type") == "refresh"

    @patch("shared.security.auth.get_settings")
    def test_custom_expiry_delta(self, mock_get: MagicMock) -> None:
        """Custom expiry should override default."""
        mock_get.return_value = _mock_settings()

        token = create_access_token("user-1", "tenant-1", expires_delta=timedelta(hours=2))
        payload = verify_token(token)
        assert payload.exp is not None
        assert payload.iat is not None
        diff = payload.exp - payload.iat
        assert abs(diff.total_seconds() - 7200) < 5


class TestTokenVerification:
    """Tests for JWT token verification."""

    @patch("shared.security.auth.get_settings")
    def test_expired_token_raises(self, mock_get: MagicMock) -> None:
        """Expired token should raise TokenError."""
        mock_get.return_value = _mock_settings()

        token = create_access_token("user-1", "tenant-1", expires_delta=timedelta(seconds=-1))
        with pytest.raises(TokenError, match="expired"):
            verify_token(token)

    @patch("shared.security.auth.get_settings")
    def test_expired_token_skip_verify(self, mock_get: MagicMock) -> None:
        """Expired token should decode when verify_exp=False."""
        mock_get.return_value = _mock_settings()

        token = create_access_token("user-1", "tenant-1", expires_delta=timedelta(seconds=-1))
        payload = verify_token(token, verify_exp=False)
        assert payload.sub == "user-1"

    @patch("shared.security.auth.get_settings")
    def test_invalid_token_raises(self, mock_get: MagicMock) -> None:
        """Malformed token should raise TokenError."""
        mock_get.return_value = _mock_settings()

        with pytest.raises(TokenError, match="Invalid"):
            verify_token("not.a.valid.token")

    @patch("shared.security.auth.get_settings")
    def test_tampered_token_raises(self, mock_get: MagicMock) -> None:
        """Tampered token should raise TokenError."""
        mock_get.return_value = _mock_settings()

        token = create_access_token("user-1", "tenant-1")
        # Tamper with the payload
        parts = token.split(".")
        parts[1] = parts[1] + "x"
        tampered = ".".join(parts)

        with pytest.raises(TokenError):
            verify_token(tampered)


class TestTokenPayload:
    """Tests for the TokenPayload class."""

    def test_payload_from_dict(self) -> None:
        """TokenPayload should parse a dict correctly."""
        import time

        now = time.time()
        payload = TokenPayload(
            {
                "sub": "user-1",
                "tenant_id": "tenant-1",
                "role": "ADMIN",
                "iat": now,
                "exp": now + 3600,
                "scopes": ["all"],
            }
        )
        assert payload.sub == "user-1"
        assert payload.tenant_id == "tenant-1"
        assert payload.role == "ADMIN"
        assert payload.iat is not None
        assert payload.exp is not None
        assert payload.scopes == ["all"]

    def test_payload_repr(self) -> None:
        """TokenPayload repr should be informative."""
        payload = TokenPayload({"sub": "u-1", "tenant_id": "t-1", "role": "TRADER"})
        r = repr(payload)
        assert "u-1" in r
        assert "t-1" in r
        assert "TRADER" in r

    def test_is_expired_false_for_future(self) -> None:
        """Token with future expiry should not be expired."""
        import time

        payload = TokenPayload({"sub": "u-1", "tenant_id": "t-1", "exp": time.time() + 3600})
        assert payload.is_expired is False

    def test_is_expired_true_for_past(self) -> None:
        """Token with past expiry should be expired."""
        import time

        payload = TokenPayload({"sub": "u-1", "tenant_id": "t-1", "exp": time.time() - 3600})
        assert payload.is_expired is True

    def test_is_expired_false_when_no_exp(self) -> None:
        """Token without exp claim should not be considered expired."""
        payload = TokenPayload({"sub": "u-1", "tenant_id": "t-1"})
        assert payload.is_expired is False

    def test_missing_fields_default(self) -> None:
        """Missing optional fields should default gracefully."""
        payload = TokenPayload({})
        assert payload.sub == ""
        assert payload.tenant_id == ""
        assert payload.role == ""
        assert payload.scopes == []
        assert payload.jti is None
