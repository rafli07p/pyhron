"""Unit tests for WebSocket first-message authentication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest

from services.api.websocket_gateway import authenticate_ws_token

# =============================================================================
# authenticate_ws_token
# =============================================================================

_TEST_SECRET = "test-jwt-secret-for-unit-tests-minimum-64-characters-long-enough"  # noqa: S105
_TEST_ALGORITHM = "HS256"


def _make_token(
    sub: str = "user-1",
    tenant_id: str = "tenant-1",
    role: str = "trader",
    expired: bool = False,
) -> str:
    payload = {
        "sub": sub,
        "tenant_id": tenant_id,
        "role": role,
        "exp": datetime.now(UTC) + (timedelta(hours=-1) if expired else timedelta(hours=1)),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm=_TEST_ALGORITHM)


class TestAuthenticateWSToken:
    @patch("services.api.websocket_gateway._get_jwt_algorithm", return_value=_TEST_ALGORITHM)
    @patch("services.api.websocket_gateway._get_jwt_secret", return_value=_TEST_SECRET)
    def test_valid_token(self, mock_secret, mock_algo) -> None:
        token = _make_token()
        claims = authenticate_ws_token(token)
        assert claims["user_id"] == "user-1"
        assert claims["tenant_id"] == "tenant-1"
        assert claims["role"] == "trader"

    @patch("services.api.websocket_gateway._get_jwt_algorithm", return_value=_TEST_ALGORITHM)
    @patch("services.api.websocket_gateway._get_jwt_secret", return_value=_TEST_SECRET)
    def test_default_role(self, mock_secret, mock_algo) -> None:
        payload = {
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = jwt.encode(payload, _TEST_SECRET, algorithm=_TEST_ALGORITHM)
        claims = authenticate_ws_token(token)
        assert claims["role"] == "viewer"

    @patch("services.api.websocket_gateway._get_jwt_algorithm", return_value=_TEST_ALGORITHM)
    @patch("services.api.websocket_gateway._get_jwt_secret", return_value=_TEST_SECRET)
    def test_expired_token_raises(self, mock_secret, mock_algo) -> None:
        token = _make_token(expired=True)
        with pytest.raises(ValueError, match="Token expired"):
            authenticate_ws_token(token)

    @patch("services.api.websocket_gateway._get_jwt_algorithm", return_value=_TEST_ALGORITHM)
    @patch("services.api.websocket_gateway._get_jwt_secret", return_value=_TEST_SECRET)
    def test_invalid_token_raises(self, mock_secret, mock_algo) -> None:
        with pytest.raises(ValueError, match="Invalid token"):
            authenticate_ws_token("not.a.valid.jwt")

    @patch("services.api.websocket_gateway._get_jwt_algorithm", return_value=_TEST_ALGORITHM)
    @patch("services.api.websocket_gateway._get_jwt_secret", return_value=_TEST_SECRET)
    def test_missing_claims_raises(self, mock_secret, mock_algo) -> None:
        payload = {
            "sub": "user-1",
            # Missing tenant_id
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = jwt.encode(payload, _TEST_SECRET, algorithm=_TEST_ALGORITHM)
        with pytest.raises(ValueError, match="Missing required claims"):
            authenticate_ws_token(token)

    @patch("services.api.websocket_gateway._get_jwt_algorithm", return_value=_TEST_ALGORITHM)
    @patch(
        "services.api.websocket_gateway._get_jwt_secret",
        return_value="wrong-secret-that-is-long-enough-for-testing-64-chars-minimum",
    )
    def test_wrong_secret_raises(self, mock_secret, mock_algo) -> None:
        token = _make_token()
        with pytest.raises(ValueError, match="Invalid token"):
            authenticate_ws_token(token)
