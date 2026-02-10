"""Tests for Telegram notification provider."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taggarr.workers.providers.telegram import TelegramProvider


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@pytest.fixture
def provider():
    """Create a TelegramProvider instance."""
    return TelegramProvider()


class TestTelegramProviderSend:
    """Tests for TelegramProvider.send method."""

    def test_send_requires_bot_token(self, provider) -> None:
        """send() raises ValueError without bot_token."""
        with pytest.raises(ValueError, match="bot_token is required"):
            run_async(provider.send("Title", "Message", {"chat_id": "123"}))

    def test_send_requires_chat_id(self, provider) -> None:
        """send() raises ValueError without chat_id."""
        with pytest.raises(ValueError, match="chat_id is required"):
            run_async(provider.send("Title", "Message", {"bot_token": "abc"}))

    def test_send_posts_to_telegram_api(self, provider) -> None:
        """send() posts message to Telegram API."""
        with patch("taggarr.workers.providers.telegram.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={"ok": True})

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            run_async(
                provider.send(
                    "Test Title",
                    "Test Message",
                    {"bot_token": "123:ABC", "chat_id": "456"},
                )
            )

            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert "123:ABC" in call_args[0][0]
            payload = call_args[1]["json"]
            assert payload["chat_id"] == "456"
            assert "Test Title" in payload["text"]
            assert "Test Message" in payload["text"]

    def test_send_raises_on_api_error(self, provider) -> None:
        """send() raises ValueError on Telegram API error."""
        with patch("taggarr.workers.providers.telegram.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(
                return_value={"ok": False, "description": "Chat not found"}
            )

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            with pytest.raises(ValueError, match="Chat not found"):
                run_async(
                    provider.send(
                        "Title",
                        "Message",
                        {"bot_token": "123:ABC", "chat_id": "456"},
                    )
                )


class TestTelegramProviderTest:
    """Tests for TelegramProvider.test method."""

    def test_test_returns_success_on_success(self, provider) -> None:
        """test() returns success tuple on successful send."""
        with patch.object(provider, "send", new=AsyncMock(return_value=None)):
            success, message = run_async(
                provider.test({"bot_token": "abc", "chat_id": "123"})
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
                provider.test({"bot_token": "abc", "chat_id": "123"})
            )

            assert success is False
            assert "Unexpected" in message

    def test_test_returns_failure_on_http_error(self, provider) -> None:
        """test() returns failure tuple on httpx.HTTPError."""
        import httpx
        with patch.object(
            provider, "send",
            new=AsyncMock(side_effect=httpx.HTTPError("Connection refused")),
        ):
            success, message = run_async(
                provider.test({"bot_token": "abc", "chat_id": "123"})
            )
            assert success is False
            assert "Telegram API failed" in message
