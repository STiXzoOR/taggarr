"""Tests for Pushover notification provider."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taggarr.workers.providers.pushover import PushoverProvider


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@pytest.fixture
def provider():
    """Create a PushoverProvider instance."""
    return PushoverProvider()


class TestPushoverProviderSend:
    """Tests for PushoverProvider.send method."""

    def test_send_requires_user_key(self, provider) -> None:
        """send() raises ValueError without user_key."""
        with pytest.raises(ValueError, match="user_key is required"):
            run_async(provider.send("Title", "Message", {"api_token": "abc"}))

    def test_send_requires_api_token(self, provider) -> None:
        """send() raises ValueError without api_token."""
        with pytest.raises(ValueError, match="api_token is required"):
            run_async(provider.send("Title", "Message", {"user_key": "abc"}))

    def test_send_posts_to_pushover_api(self, provider) -> None:
        """send() posts message to Pushover API."""
        with patch("taggarr.workers.providers.pushover.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={"status": 1})

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            run_async(
                provider.send(
                    "Test Title",
                    "Test Message",
                    {"user_key": "user123", "api_token": "token123"},
                )
            )

            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert "pushover.net" in call_args[0][0]
            payload = call_args[1]["data"]
            assert payload["user"] == "user123"
            assert payload["token"] == "token123"
            assert payload["title"] == "Test Title"
            assert payload["message"] == "Test Message"

    def test_send_raises_on_api_error(self, provider) -> None:
        """send() raises ValueError on Pushover API error."""
        with patch("taggarr.workers.providers.pushover.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(
                return_value={"status": 0, "errors": ["invalid user key"]}
            )

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            with pytest.raises(ValueError, match="invalid user key"):
                run_async(
                    provider.send(
                        "Title",
                        "Message",
                        {"user_key": "bad", "api_token": "token"},
                    )
                )


class TestPushoverProviderTest:
    """Tests for PushoverProvider.test method."""

    def test_test_returns_success_on_success(self, provider) -> None:
        """test() returns success tuple on successful send."""
        with patch.object(provider, "send", new=AsyncMock(return_value=None)):
            success, message = run_async(
                provider.test({"user_key": "user", "api_token": "token"})
            )

            assert success is True
            assert "successfully" in message

    def test_test_returns_failure_on_missing_settings(self, provider) -> None:
        """test() returns failure tuple on missing settings."""
        success, message = run_async(provider.test({}))

        assert success is False
        assert "required" in message

    def test_test_returns_failure_on_unexpected_error(self, provider) -> None:
        """test() returns failure tuple on unexpected error."""
        with patch.object(
            provider,
            "send",
            new=AsyncMock(side_effect=RuntimeError("Unexpected")),
        ):
            success, message = run_async(
                provider.test({"user_key": "user", "api_token": "token"})
            )

            assert success is False
            assert "Unexpected" in message

    def test_send_includes_priority_when_set(self, provider) -> None:
        """send() includes priority in payload when specified."""
        with patch("taggarr.workers.providers.pushover.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={"status": 1})

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            run_async(
                provider.send(
                    "Title", "Message",
                    {"user_key": "user", "api_token": "token", "priority": 1},
                )
            )

            payload = mock_instance.post.call_args[1]["data"]
            assert payload["priority"] == 1

    def test_test_returns_failure_on_http_error(self, provider) -> None:
        """test() returns failure tuple on httpx.HTTPError."""
        import httpx
        with patch.object(
            provider, "send",
            new=AsyncMock(side_effect=httpx.HTTPError("Connection refused")),
        ):
            success, message = run_async(
                provider.test({"user_key": "user", "api_token": "token"})
            )
            assert success is False
            assert "Pushover API failed" in message

    def test_send_raises_on_api_error_without_errors_field(self, provider) -> None:
        """send() raises ValueError with default error message."""
        with patch("taggarr.workers.providers.pushover.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={"status": 0})  # No errors field

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            with pytest.raises(ValueError, match="Unknown error"):
                run_async(
                    provider.send(
                        "Title",
                        "Message",
                        {"user_key": "user", "api_token": "token"},
                    )
                )
