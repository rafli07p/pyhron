from __future__ import annotations


class DecryptionError(Exception):
    """Raised when decryption fails."""


class InvalidKeyError(Exception):
    """Raised for invalid key (wrong size, format, etc.)."""


class TamperedDataError(Exception):
    """Raised when data integrity check fails (GCM tag mismatch)."""
