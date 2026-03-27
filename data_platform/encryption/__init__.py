"""
Encryption service for the Pyhron data platform.

Provides AES-256 encryption via Fernet for strategy IP protection,
compliance data, and sensitive market data at rest.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)

# Constants
_CHUNK_SIZE: int = 64 * 1024  # 64 KiB file-streaming chunk size
_KEY_ROTATION_HEADER = b"PYHRON_ENC_V1"


class EncryptionError(Exception):
    """Raised when an encryption or decryption operation fails."""


class KeyManagementError(Exception):
    """Raised on key-lifecycle errors (missing key, rotation failure)."""


# EncryptionService
class EncryptionService:
    """AES-256 encryption service backed by ``cryptography.fernet``.

    Parameters
    ----------
    encryption_key : str | bytes | None
        A Fernet-compatible base64 key.  When *None* the service reads
        ``PYHRON_ENCRYPTION_KEY`` from the environment.
    tenant_id : str
        Tenant identifier used to derive per-tenant sub-keys so that one
        master key can serve multiple tenants without cross-read risk.
    previous_keys : list[str | bytes] | None
        Optional list of prior Fernet keys (oldest-last) used for
        transparent decryption during key-rotation windows.
    """

    def __init__(
        self,
        encryption_key: str | bytes | None = None,
        tenant_id: str = "default",
        previous_keys: list[str | bytes] | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self._log = logger.bind(tenant_id=tenant_id, component="EncryptionService")

        # Resolve primary key ------------------------------------------------
        raw_key = encryption_key or os.environ.get("PYHRON_ENCRYPTION_KEY")
        if raw_key is None:
            raise KeyManagementError(
                "No encryption key supplied and PYHRON_ENCRYPTION_KEY is not set."
            )
        self._primary_key = self._normalise_key(raw_key)
        self._primary_fernet = Fernet(self._primary_key)

        # Build MultiFernet for rotation support ------------------------------
        fernets = [self._primary_fernet]
        self._previous_keys: list[bytes] = []
        for k in previous_keys or []:
            norm = self._normalise_key(k)
            self._previous_keys.append(norm)
            fernets.append(Fernet(norm))
        self._multi_fernet = MultiFernet(fernets)

        # Derive a per-tenant sub-key for data isolation ----------------------
        self._tenant_fernet = Fernet(self._derive_tenant_key(self._primary_key, tenant_id))

        self._log.info("encryption_service_initialised", has_previous_keys=bool(previous_keys))

    # Key helpers
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet-compatible encryption key."""
        return Fernet.generate_key().decode()

    @staticmethod
    def _normalise_key(key: str | bytes) -> bytes:
        if isinstance(key, str):
            key = key.encode()
        # Validate the key is Fernet-compatible (will raise on bad key)
        Fernet(key)
        return key

    @staticmethod
    def _derive_tenant_key(master_key: bytes, tenant_id: str) -> bytes:
        """Derive a deterministic Fernet key for *tenant_id* from *master_key*."""
        digest = hashlib.sha256(master_key + tenant_id.encode()).digest()
        return base64.urlsafe_b64encode(digest)

    # Core encrypt / decrypt
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, max=1),
        retry=retry_if_exception_type(OSError),
        reraise=True,
    )
    def encrypt_data(self, plaintext: str | bytes, *, use_tenant_key: bool = True) -> bytes:
        """Encrypt *plaintext* and return ciphertext bytes.

        Parameters
        ----------
        plaintext : str | bytes
            Data to encrypt.
        use_tenant_key : bool
            When ``True`` (default) the per-tenant derived key is used,
            providing tenant isolation.  Set ``False`` to use the master key.
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")
        fernet = self._tenant_fernet if use_tenant_key else self._primary_fernet
        try:
            token = fernet.encrypt(plaintext)
            self._log.debug("data_encrypted", size=len(plaintext), tenant_isolated=use_tenant_key)
            return token
        except Exception as exc:
            self._log.error("encrypt_data_failed", error=str(exc))
            raise EncryptionError(f"Encryption failed: {exc}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, max=1),
        retry=retry_if_exception_type(OSError),
        reraise=True,
    )
    def decrypt_data(self, token: bytes, *, use_tenant_key: bool = True) -> bytes:
        """Decrypt a Fernet *token* and return plaintext bytes.

        When ``use_tenant_key`` is ``False`` the ``MultiFernet`` stack is
        used, which transparently tries the primary key followed by any
        previous rotation keys.
        """
        try:
            if use_tenant_key:
                plaintext = self._tenant_fernet.decrypt(token)
            else:
                plaintext = self._multi_fernet.decrypt(token)
            self._log.debug("data_decrypted", size=len(plaintext))
            return plaintext
        except InvalidToken as exc:
            self._log.error("decrypt_data_failed_invalid_token")
            raise EncryptionError("Decryption failed: invalid token or wrong key.") from exc
        except Exception as exc:
            self._log.error("decrypt_data_failed", error=str(exc))
            raise EncryptionError(f"Decryption failed: {exc}") from exc

    # File encrypt / decrypt
    def encrypt_file(self, src_path: str | Path, dst_path: str | Path | None = None) -> Path:
        """Encrypt a file on disk.

        Parameters
        ----------
        src_path : str | Path
            Path to the plaintext file.
        dst_path : str | Path | None
            Destination for the ciphertext.  Defaults to ``<src_path>.enc``.

        Returns
        -------
        Path
            Path to the encrypted output file.
        """
        src = Path(src_path)
        dst = Path(dst_path) if dst_path else src.with_suffix(src.suffix + ".enc")
        self._log.info("encrypt_file_start", src=str(src), dst=str(dst))

        try:
            plaintext = src.read_bytes()
            ciphertext = self._tenant_fernet.encrypt(plaintext)
            dst.write_bytes(_KEY_ROTATION_HEADER + b"\n" + ciphertext)
            self._log.info("encrypt_file_done", src=str(src), dst=str(dst), size=len(plaintext))
            return dst
        except Exception as exc:
            self._log.error("encrypt_file_failed", src=str(src), error=str(exc))
            raise EncryptionError(f"File encryption failed: {exc}") from exc

    def decrypt_file(self, src_path: str | Path, dst_path: str | Path | None = None) -> Path:
        """Decrypt a previously-encrypted file.

        Parameters
        ----------
        src_path : str | Path
            Path to the ``.enc`` ciphertext file.
        dst_path : str | Path | None
            Destination for the plaintext.  Defaults to *src_path* with the
            trailing ``.enc`` removed.

        Returns
        -------
        Path
            Path to the decrypted output file.
        """
        src = Path(src_path)
        if dst_path:
            dst = Path(dst_path)
        else:
            name = src.name
            if name.endswith(".enc"):
                name = name[: -len(".enc")]
            dst = src.with_name(name + ".dec")

        self._log.info("decrypt_file_start", src=str(src))
        try:
            raw = src.read_bytes()
            # Strip header if present
            if raw.startswith(_KEY_ROTATION_HEADER):
                raw = raw[len(_KEY_ROTATION_HEADER) + 1 :]  # +1 for newline
            plaintext = self._tenant_fernet.decrypt(raw)
            dst.write_bytes(plaintext)
            self._log.info("decrypt_file_done", dst=str(dst), size=len(plaintext))
            return dst
        except InvalidToken as exc:
            self._log.error("decrypt_file_invalid_token", src=str(src))
            raise EncryptionError("File decryption failed: invalid token or wrong key.") from exc
        except Exception as exc:
            self._log.error("decrypt_file_failed", src=str(src), error=str(exc))
            raise EncryptionError(f"File decryption failed: {exc}") from exc

    # Key rotation
    def rotate_key(self, new_key: str | bytes | None = None) -> str:
        """Rotate to a new encryption key.

        The current primary key is demoted to the previous-keys list so
        that data encrypted under it can still be decrypted transparently.

        Parameters
        ----------
        new_key : str | bytes | None
            The new Fernet key.  If ``None`` a fresh key is generated.

        Returns
        -------
        str
            The new primary key (base64-encoded string).
        """
        if new_key is None:
            new_key_bytes = Fernet.generate_key()
        else:
            new_key_bytes = self._normalise_key(new_key)

        # Demote current primary
        self._previous_keys.insert(0, self._primary_key)
        self._primary_key = new_key_bytes
        self._primary_fernet = Fernet(self._primary_key)

        # Rebuild MultiFernet
        fernets = [self._primary_fernet] + [Fernet(k) for k in self._previous_keys]
        self._multi_fernet = MultiFernet(fernets)

        # Rebuild tenant key
        self._tenant_fernet = Fernet(self._derive_tenant_key(self._primary_key, self.tenant_id))

        self._log.info(
            "key_rotated",
            previous_key_count=len(self._previous_keys),
            timestamp=datetime.now(UTC).isoformat(),
        )
        return new_key_bytes.decode()

    # Convenience helpers
    def encrypt_string(self, value: str) -> str:
        """Encrypt a string and return a base64-encoded ciphertext string."""
        return self.encrypt_data(value).decode()

    def decrypt_string(self, token_str: str) -> str:
        """Decrypt a base64-encoded ciphertext string back to plaintext."""
        return self.decrypt_data(token_str.encode()).decode()


__all__ = [
    "EncryptionError",
    "EncryptionService",
    "KeyManagementError",
]
