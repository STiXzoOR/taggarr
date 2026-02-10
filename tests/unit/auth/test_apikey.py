"""Tests for API key generation and verification."""

from taggarr.auth.apikey import generate_api_key, hash_api_key, verify_api_key


class TestGenerateApiKey:
    """Tests for generate_api_key function."""

    def test_generate_api_key_returns_key(self) -> None:
        """Generate_api_key returns a string key."""
        key = generate_api_key()

        assert isinstance(key, str)
        assert len(key) == 32  # 24 bytes = 32 base64 chars


class TestHashApiKey:
    """Tests for hash_api_key function."""

    def test_hash_api_key_returns_hash(self) -> None:
        """Hash_api_key returns SHA256 hash (hex string, 64 chars)."""
        key = "test_api_key_12345678901234567890"

        hashed = hash_api_key(key)

        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256 hex string is 64 chars
        # Verify it's a valid hex string
        int(hashed, 16)


class TestVerifyApiKey:
    """Tests for verify_api_key function."""

    def test_verify_api_key_correct(self) -> None:
        """Verify_api_key returns True for matching key."""
        key = generate_api_key()
        stored_hash = hash_api_key(key)

        result = verify_api_key(key, stored_hash)

        assert result is True

    def test_verify_api_key_incorrect(self) -> None:
        """Verify_api_key returns False for wrong key."""
        key = generate_api_key()
        stored_hash = hash_api_key(key)
        wrong_key = generate_api_key()

        result = verify_api_key(wrong_key, stored_hash)

        assert result is False
