"""
Tests for the encryption service.

Validates AES-256-GCM encryption/decryption, key derivation, field-level
encryption for PII/sensitive data, and compliance with UU PDP requirements.
"""

from __future__ import annotations

import json
import os

import pytest

# Future paths:
#   from data_platform.encryption import EncryptionService, EncryptionError, KeyManagementError
#   FieldEncryptor, KeyDerivationService, DecryptionError, InvalidKeyError, TamperedDataError — not yet implemented
pytest.importorskip("pyhron.shared.encryption", reason="module not yet implemented")
from pyhron.shared.encryption.exceptions import (
    DecryptionError,
    InvalidKeyError,
    TamperedDataError,
)
from pyhron.shared.encryption.service import (
    EncryptionService,
    FieldEncryptor,
    KeyDerivationService,
)


# Fixtures
@pytest.fixture
def encryption_key() -> bytes:
    """Generate a valid 256-bit encryption key."""
    return os.urandom(32)


@pytest.fixture
def encryption_service(encryption_key: bytes) -> EncryptionService:
    """Encryption service with a fresh key."""
    return EncryptionService(master_key=encryption_key)


@pytest.fixture
def key_derivation_service(encryption_key: bytes) -> KeyDerivationService:
    """Key derivation service instance."""
    return KeyDerivationService(master_key=encryption_key)


@pytest.fixture
def field_encryptor(encryption_service: EncryptionService) -> FieldEncryptor:
    """Field-level encryptor for structured data."""
    return FieldEncryptor(encryption_service=encryption_service)


# Basic Encryption/Decryption Tests
class TestBasicEncryption:
    """Tests for core encrypt/decrypt operations."""

    def test_encrypt_decrypt_roundtrip(self, encryption_service: EncryptionService):
        """Data should survive encrypt/decrypt roundtrip."""
        plaintext = b"Sensitive trading data: position_size=1000000"
        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertext(self, encryption_service: EncryptionService):
        """Same plaintext should produce different ciphertexts (unique nonce)."""
        plaintext = b"Same data encrypted twice"
        ct1 = encryption_service.encrypt(plaintext)
        ct2 = encryption_service.encrypt(plaintext)
        assert ct1 != ct2

    def test_ciphertext_is_not_plaintext(self, encryption_service: EncryptionService):
        """Ciphertext should not contain plaintext."""
        plaintext = b"This should not be readable"
        ciphertext = encryption_service.encrypt(plaintext)
        assert plaintext not in ciphertext

    @pytest.mark.parametrize(
        "plaintext",
        [
            b"",
            b"a",
            b"Short",
            b"A" * 1024,
            b"A" * 1024 * 1024,  # 1MB
            bytes(range(256)),  # All byte values
        ],
    )
    def test_various_plaintext_sizes(self, encryption_service: EncryptionService, plaintext: bytes):
        """Various plaintext sizes should be handled correctly."""
        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_unicode_string_encryption(self, encryption_service: EncryptionService):
        """Unicode strings should be encrypted/decrypted correctly."""
        text = "Nama: Budi Santoso, Alamat: Jl. Sudirman No. 1, Jakarta"
        plaintext = text.encode("utf-8")
        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)
        assert decrypted.decode("utf-8") == text


# Tampering Detection Tests
class TestTamperingDetection:
    """Tests for authenticated encryption (GCM tag validation)."""

    def test_modified_ciphertext_detected(self, encryption_service: EncryptionService):
        """Modified ciphertext should fail authentication."""
        plaintext = b"Tamper-proof data"
        ciphertext = bytearray(encryption_service.encrypt(plaintext))

        # Flip a byte in the ciphertext body
        if len(ciphertext) > 20:
            ciphertext[20] ^= 0xFF

        with pytest.raises((DecryptionError, TamperedDataError)):
            encryption_service.decrypt(bytes(ciphertext))

    def test_truncated_ciphertext_detected(self, encryption_service: EncryptionService):
        """Truncated ciphertext should fail."""
        plaintext = b"Data integrity check"
        ciphertext = encryption_service.encrypt(plaintext)

        with pytest.raises((DecryptionError, TamperedDataError)):
            encryption_service.decrypt(ciphertext[: len(ciphertext) // 2])

    def test_wrong_key_fails(self, encryption_service: EncryptionService):
        """Decryption with wrong key should fail."""
        plaintext = b"Key-specific encryption"
        ciphertext = encryption_service.encrypt(plaintext)

        wrong_key = os.urandom(32)
        wrong_service = EncryptionService(master_key=wrong_key)

        with pytest.raises((DecryptionError, TamperedDataError)):
            wrong_service.decrypt(ciphertext)

    def test_empty_ciphertext_fails(self, encryption_service: EncryptionService):
        """Empty ciphertext should raise an error."""
        with pytest.raises((DecryptionError, ValueError)):
            encryption_service.decrypt(b"")


# Key Derivation Tests
class TestKeyDerivation:
    """Tests for key derivation from master key."""

    def test_derive_deterministic_key(self, key_derivation_service: KeyDerivationService):
        """Same context should produce the same derived key."""
        key1 = key_derivation_service.derive_key(context="user_pii")
        key2 = key_derivation_service.derive_key(context="user_pii")
        assert key1 == key2

    def test_different_contexts_different_keys(self, key_derivation_service: KeyDerivationService):
        """Different contexts should produce different derived keys."""
        key_pii = key_derivation_service.derive_key(context="user_pii")
        key_trading = key_derivation_service.derive_key(context="trading_data")
        assert key_pii != key_trading

    def test_derived_key_length(self, key_derivation_service: KeyDerivationService):
        """Derived keys should be 256 bits (32 bytes)."""
        key = key_derivation_service.derive_key(context="test")
        assert len(key) == 32

    def test_invalid_master_key_length(self):
        """Invalid master key length should raise an error."""
        with pytest.raises(InvalidKeyError):
            KeyDerivationService(master_key=b"too_short")


# Field-Level Encryption Tests
class TestFieldEncryption:
    """Tests for field-level encryption of structured data."""

    def test_encrypt_specific_fields(self, field_encryptor: FieldEncryptor):
        """Only specified fields should be encrypted."""
        record = {
            "user_id": "USR-12345",
            "name": "Budi Santoso",
            "email": "budi@example.com",
            "nik": "3201012345678901",  # Indonesian national ID
            "balance": "50000000.00",
            "strategy": "momentum_v1",
        }
        sensitive_fields = ["name", "email", "nik"]

        encrypted_record = field_encryptor.encrypt_fields(
            record=record,
            fields=sensitive_fields,
        )

        # Sensitive fields should be encrypted
        assert encrypted_record["name"] != "Budi Santoso"
        assert encrypted_record["email"] != "budi@example.com"
        assert encrypted_record["nik"] != "3201012345678901"

        # Non-sensitive fields should remain unchanged
        assert encrypted_record["user_id"] == "USR-12345"
        assert encrypted_record["balance"] == "50000000.00"
        assert encrypted_record["strategy"] == "momentum_v1"

    def test_decrypt_specific_fields(self, field_encryptor: FieldEncryptor):
        """Encrypted fields should be decryptable."""
        record = {
            "user_id": "USR-12345",
            "name": "Budi Santoso",
            "email": "budi@example.com",
            "nik": "3201012345678901",
        }
        sensitive_fields = ["name", "email", "nik"]

        encrypted = field_encryptor.encrypt_fields(record, sensitive_fields)
        decrypted = field_encryptor.decrypt_fields(encrypted, sensitive_fields)

        assert decrypted == record

    def test_encrypt_preserves_field_presence(self, field_encryptor: FieldEncryptor):
        """All fields should be present after encryption."""
        record = {"field_a": "value_a", "field_b": "value_b", "field_c": "value_c"}

        encrypted = field_encryptor.encrypt_fields(record, ["field_b"])
        assert set(encrypted.keys()) == set(record.keys())

    def test_encrypt_missing_field_raises(self, field_encryptor: FieldEncryptor):
        """Encrypting a non-existent field should raise an error."""
        record = {"name": "Test"}

        with pytest.raises(KeyError):
            field_encryptor.encrypt_fields(record, ["nonexistent_field"])

    def test_nested_field_encryption(self, field_encryptor: FieldEncryptor):
        """Nested fields should be encryptable with dot notation."""
        record = {
            "user": {
                "personal": {
                    "name": "Budi Santoso",
                    "nik": "3201012345678901",
                },
                "preferences": {
                    "theme": "dark",
                },
            },
            "account_type": "premium",
        }

        encrypted = field_encryptor.encrypt_fields(
            record,
            fields=["user.personal.name", "user.personal.nik"],
        )

        assert encrypted["user"]["personal"]["name"] != "Budi Santoso"
        assert encrypted["user"]["preferences"]["theme"] == "dark"
        assert encrypted["account_type"] == "premium"


# Compliance Tests (UU PDP)
class TestComplianceEncryption:
    """Tests ensuring encryption meets UU PDP compliance requirements."""

    def test_pii_not_in_encrypted_output(self, encryption_service: EncryptionService):
        """PII should not appear in any form in encrypted output."""
        pii_data = json.dumps(
            {
                "nik": "3201012345678901",
                "nama": "Budi Santoso",
                "alamat": "Jl. Sudirman No. 1, Jakarta Selatan",
                "nomor_telepon": "+6281234567890",
                "email": "budi.santoso@email.co.id",
            }
        ).encode("utf-8")

        ciphertext = encryption_service.encrypt(pii_data)
        ciphertext_str = ciphertext.hex()

        # None of the PII values should appear in hex-encoded ciphertext
        assert "3201012345678901" not in ciphertext_str
        assert "Budi" not in ciphertext_str.lower()
        assert "sudirman" not in ciphertext_str.lower()

    def test_encryption_uses_aes_256(self, encryption_service: EncryptionService):
        """Encryption should use AES-256 (key size validation)."""
        assert encryption_service.key_size == 256
        assert encryption_service.algorithm == "AES-256-GCM"

    def test_audit_trail_for_encryption(self, encryption_service: EncryptionService):
        """Encryption operations should be auditable."""
        plaintext = b"Auditable encryption operation"
        encryption_service.encrypt(plaintext)

        # Verify metadata is available for audit
        metadata = encryption_service.get_last_operation_metadata()
        assert metadata is not None
        assert "timestamp" in metadata
        assert "operation" in metadata
        assert metadata["operation"] == "encrypt"
        assert "key_id" in metadata

    def test_key_rotation_support(self, encryption_key: bytes):
        """Service should support key rotation."""
        old_service = EncryptionService(master_key=encryption_key)
        plaintext = b"Data encrypted with old key"
        old_ciphertext = old_service.encrypt(plaintext)

        # Rotate to new key
        new_key = os.urandom(32)
        new_service = EncryptionService(master_key=new_key)

        # Old ciphertext should not be decryptable with new key
        with pytest.raises((DecryptionError, TamperedDataError)):
            new_service.decrypt(old_ciphertext)

        # Re-encrypt with new key
        decrypted = old_service.decrypt(old_ciphertext)
        new_ciphertext = new_service.encrypt(decrypted)
        re_decrypted = new_service.decrypt(new_ciphertext)

        assert re_decrypted == plaintext
