from __future__ import annotations

import base64
import copy
import hashlib
import os
from datetime import UTC, datetime

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from pyhron.shared.encryption.exceptions import (
    DecryptionError,
    InvalidKeyError,
    TamperedDataError,
)

NONCE_SIZE = 12
TAG_SIZE = 16


class EncryptionService:
    """AES-256-GCM encryption service."""

    def __init__(self, master_key: bytes) -> None:
        self._master_key = master_key
        self._aesgcm = AESGCM(master_key)
        self._key_id = hashlib.sha256(master_key).hexdigest()[:16]
        self._last_metadata: dict | None = None

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(NONCE_SIZE)
        ct_with_tag = self._aesgcm.encrypt(nonce, plaintext, None)
        self._last_metadata = {
            "timestamp": datetime.now(UTC).isoformat(),
            "operation": "encrypt",
            "key_id": self._key_id,
        }
        return nonce + ct_with_tag

    def decrypt(self, ciphertext: bytes) -> bytes:
        if not ciphertext:
            raise DecryptionError("Ciphertext is empty")

        if len(ciphertext) < NONCE_SIZE + TAG_SIZE:
            raise DecryptionError("Ciphertext too short")

        nonce = ciphertext[:NONCE_SIZE]
        ct_with_tag = ciphertext[NONCE_SIZE:]

        try:
            plaintext = self._aesgcm.decrypt(nonce, ct_with_tag, None)
        except Exception as exc:
            raise TamperedDataError("Data integrity check failed") from exc

        self._last_metadata = {
            "timestamp": datetime.now(UTC).isoformat(),
            "operation": "decrypt",
            "key_id": self._key_id,
        }
        return plaintext

    @property
    def key_size(self) -> int:
        return 256

    @property
    def algorithm(self) -> str:
        return "AES-256-GCM"

    def get_last_operation_metadata(self) -> dict | None:
        return self._last_metadata


class KeyDerivationService:
    """HKDF-SHA256 key derivation from a master key."""

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) != 32:
            raise InvalidKeyError(
                f"Master key must be 32 bytes, got {len(master_key)}"
            )
        self._master_key = master_key

    def derive_key(self, context: str) -> bytes:
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=context.encode("utf-8"),
        )
        return hkdf.derive(self._master_key)


def _get_nested(obj: dict, keys: list[str]) -> object:
    for key in keys:
        obj = obj[key]
    return obj


def _set_nested(obj: dict, keys: list[str], value: object) -> None:
    for key in keys[:-1]:
        obj = obj[key]
    obj[keys[-1]] = value


class FieldEncryptor:
    """Encrypts/decrypts individual fields in a dict, including nested fields."""

    def __init__(self, encryption_service: EncryptionService) -> None:
        self._service = encryption_service

    def encrypt_fields(self, record: dict, fields: list[str]) -> dict:
        result = copy.deepcopy(record)
        for field in fields:
            keys = field.split(".")
            value = _get_nested(result, keys)
            plaintext = str(value).encode("utf-8")
            encrypted = self._service.encrypt(plaintext)
            _set_nested(result, keys, base64.b64encode(encrypted).decode("ascii"))
        return result

    def decrypt_fields(self, record: dict, fields: list[str]) -> dict:
        result = copy.deepcopy(record)
        for field in fields:
            keys = field.split(".")
            value = _get_nested(result, keys)
            encrypted = base64.b64decode(value)
            decrypted = self._service.decrypt(encrypted)
            _set_nested(result, keys, decrypted.decode("utf-8"))
        return result
