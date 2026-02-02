"""Password hashing service using PBKDF2-SHA256."""

import hashlib
import secrets

# OWASP recommendation for PBKDF2-SHA256 (2023+)
DEFAULT_ITERATIONS = 600000
SALT_BYTES = 32
HASH_BYTES = 32


def hash_password(password: str) -> tuple[str, str, int]:
    """Hash a password using PBKDF2-SHA256.

    Args:
        password: The plaintext password to hash.

    Returns:
        A tuple of (hash, salt, iterations) where hash and salt are hex strings.
    """
    salt = secrets.token_bytes(SALT_BYTES)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        DEFAULT_ITERATIONS,
        dklen=HASH_BYTES,
    )

    return password_hash.hex(), salt.hex(), DEFAULT_ITERATIONS


def verify_password(
    password: str, stored_hash: str, salt: str, iterations: int
) -> bool:
    """Verify a password against a stored hash.

    Args:
        password: The plaintext password to verify.
        stored_hash: The stored password hash as a hex string.
        salt: The salt used for hashing as a hex string.
        iterations: The number of PBKDF2 iterations used.

    Returns:
        True if the password matches, False otherwise.
    """
    salt_bytes = bytes.fromhex(salt)

    computed_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        iterations,
        dklen=HASH_BYTES,
    )

    return secrets.compare_digest(computed_hash.hex(), stored_hash)
