"""Authentication module for Pyhron Terminal.

Manages JWT credential storage, validation, and interactive login.
Credentials are stored at ``~/.pyhron/credentials.json`` with 0o600
permissions.  Tokens are never written to logs.
"""

from __future__ import annotations

import getpass
import json
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

_CREDENTIALS_DIR = Path.home() / ".pyhron"
_CREDENTIALS_FILE = _CREDENTIALS_DIR / "credentials.json"
_TOKEN_REFRESH_WINDOW_SECONDS = 300  # refresh if expiring within 5 min


def _ensure_dir() -> None:
    _CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)


def _check_permissions(path: Path) -> bool:
    """Return True if file permissions are 0o600 or stricter."""
    if not path.exists():
        return True
    mode = stat.S_IMODE(path.stat().st_mode)
    return mode <= 0o600


def _write_credentials(data: dict[str, Any]) -> None:
    _ensure_dir()
    _CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))
    _CREDENTIALS_FILE.chmod(0o600)


def load_credentials(env: str = "paper") -> dict[str, str] | None:
    """Load cached credentials for the given environment.

    Returns
    -------
    dict | None
        ``{"access_token": ..., "expires_at": ..., "username": ...}``
        or None if not available or expired.
    """
    if not _CREDENTIALS_FILE.exists():
        return None

    if not _check_permissions(_CREDENTIALS_FILE):
        sys.stdout.write(
            f"ERROR: {_CREDENTIALS_FILE} has permissions broader than 0600.\nRun: chmod 600 {_CREDENTIALS_FILE}\n"
        )
        return None

    data = json.loads(_CREDENTIALS_FILE.read_text())
    env_data = data.get(env)
    if not env_data:
        return None

    # Check expiry
    expires_at = env_data.get("expires_at", "")
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            remaining = (exp - datetime.now(UTC)).total_seconds()
            if remaining <= 0:
                logger.info("token_expired", env=env, username=env_data.get("username"))
                return None
        except (ValueError, TypeError):
            return None

    return {
        "access_token": env_data["access_token"],
        "expires_at": env_data.get("expires_at", ""),
        "username": env_data.get("username", ""),
    }


def token_needs_refresh(env: str = "paper") -> bool:
    """Check if the token will expire within the refresh window."""
    creds = load_credentials(env)
    if not creds:
        return True
    expires_at = creds.get("expires_at", "")
    if not expires_at:
        return False
    try:
        exp = datetime.fromisoformat(expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        remaining = (exp - datetime.now(UTC)).total_seconds()
        return remaining < _TOKEN_REFRESH_WINDOW_SECONDS
    except (ValueError, TypeError):
        return True


def save_credentials(
    env: str,
    access_token: str,
    expires_at: str,
    username: str,
) -> None:
    """Persist credentials for the given environment."""
    data: dict[str, Any] = {}
    if _CREDENTIALS_FILE.exists() and _check_permissions(_CREDENTIALS_FILE):
        data = json.loads(_CREDENTIALS_FILE.read_text())

    data[env] = {
        "access_token": access_token,
        "expires_at": expires_at,
        "username": username,
    }
    _write_credentials(data)
    logger.info("credentials_saved", env=env, username=username, expires_at=expires_at)


async def authenticate_interactive(
    base_url: str,
    env: str = "paper",
) -> dict[str, str]:
    """Prompt for username/password and authenticate against the API.

    Returns the credential dict on success.  Raises SystemExit on failure.
    """
    sys.stdout.write(f"Pyhron Terminal — Login ({env})\n")
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/login",
                json={"username": username, "password": password},
            )

        # Overwrite password in memory
        password = "0" * len(password)
        del password

        if resp.status_code != 200:
            sys.stdout.write("Authentication failed.\n")
            raise SystemExit(1)

        body = resp.json()
        token = body.get("access_token", body.get("token", ""))
        expires = body.get("expires_at", "")

        save_credentials(env, token, expires, username)
        return {"access_token": token, "expires_at": expires, "username": username}

    except httpx.ConnectError:
        # Overwrite password
        password = "0" * 8  # noqa: F841
        sys.stdout.write(f"Cannot connect to {base_url}\n")
        raise SystemExit(1) from None
