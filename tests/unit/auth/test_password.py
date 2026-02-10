"""Tests for password hashing service."""

from taggarr.auth.password import hash_password, verify_password


class TestHashPassword:
    """Tests for hash_password function."""

    def test_hash_password_returns_hash_and_salt(self) -> None:
        """hash_password returns a tuple of (hash, salt, iterations)."""
        result = hash_password("test_password")

        assert isinstance(result, tuple)
        assert len(result) == 3

        password_hash, salt, iterations = result

        # Hash should be a hex string (64 chars for 32 bytes)
        assert isinstance(password_hash, str)
        assert len(password_hash) == 64

        # Salt should be a hex string (64 chars for 32 bytes)
        assert isinstance(salt, str)
        assert len(salt) == 64

        # Iterations should be the OWASP recommended value
        assert isinstance(iterations, int)
        assert iterations == 600000

    def test_hash_password_different_salts(self) -> None:
        """Each call generates unique salt."""
        result1 = hash_password("same_password")
        result2 = hash_password("same_password")

        hash1, salt1, _ = result1
        hash2, salt2, _ = result2

        # Salts should be different
        assert salt1 != salt2

        # Hashes should also be different due to different salts
        assert hash1 != hash2


class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_verify_password_correct(self) -> None:
        """verify_password returns True for correct password."""
        password = "my_secure_password"
        password_hash, salt, iterations = hash_password(password)

        result = verify_password(password, password_hash, salt, iterations)

        assert result is True

    def test_verify_password_incorrect(self) -> None:
        """verify_password returns False for wrong password."""
        password = "my_secure_password"
        password_hash, salt, iterations = hash_password(password)

        result = verify_password("wrong_password", password_hash, salt, iterations)

        assert result is False
