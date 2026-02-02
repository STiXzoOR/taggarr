"""API key generation and verification."""

import hashlib
import secrets


def generate_api_key() -> str:
    """Generate a 32-character API key.

    Returns:
        A URL-safe base64 string (24 bytes = 32 characters).
    """
    return secrets.token_urlsafe(24)


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA256.

    Args:
        key: The API key to hash.

    Returns:
        A 64-character hex string representing the SHA256 hash.
    """
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, stored_hash: str) -> bool:
    """Verify an API key against a stored hash.

    Args:
        key: The API key to verify.
        stored_hash: The stored SHA256 hash to compare against.

    Returns:
        True if the key matches the hash, False otherwise.
    """
    computed_hash = hash_api_key(key)
    return secrets.compare_digest(computed_hash, stored_hash)
