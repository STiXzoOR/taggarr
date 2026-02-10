"""Tests for Discord notification provider."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taggarr.workers.providers.discord import DiscordProvider


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@pytest.fixture
def provider():
    """Create a DiscordProvider instance."""
    return DiscordProvider()


class TestDiscordProviderSend:
    """Tests for DiscordProvider.send method."""

    def test_send_requires_webhook_url(self, provider) -> None:
        """send() raises ValueError without webhook_url."""
        with pytest.raises(ValueError, match="webhook_url is required"):
            run_async(provider.send("Title", "Message", {}))

    def test_send_posts_to_webhook(self, provider) -> None:
        """send() posts embed to webhook URL."""
        with patch("taggarr.workers.providers.discord.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            run_async(
                provider.send(
                    "Test Title",
                    "Test Message",
                    {"webhook_url": "https://discord.com/api/webhooks/123/abc"},
                )
            )

            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert call_args[0][0] == "https://discord.com/api/webhooks/123/abc"
            payload = call_args[1]["json"]
            assert payload["embeds"][0]["title"] == "Test Title"
            assert payload["embeds"][0]["description"] == "Test Message"

    def test_send_raises_on_http_error(self, provider) -> None:
        """send() raises on HTTP error."""
        import httpx

        with patch("taggarr.workers.providers.discord.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError(
                    "Error", request=MagicMock(), response=MagicMock()
                )
            )

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            with pytest.raises(httpx.HTTPStatusError):
                run_async(
                    provider.send(
                        "Title",
                        "Message",
                        {"webhook_url": "https://discord.com/api/webhooks/123/abc"},
                    )
                )


class TestDiscordProviderTest:
    """Tests for DiscordProvider.test method."""

    def test_test_returns_success_on_success(self, provider) -> None:
        """test() returns success tuple on successful send."""
        with patch.object(provider, "send", new=AsyncMock(return_value=None)):
            success, message = run_async(
                provider.test({"webhook_url": "https://example.com"})
            )

            assert success is True
            assert "successfully" in message

    def test_test_returns_failure_on_value_error(self, provider) -> None:
        """test() returns failure tuple on ValueError."""
        success, message = run_async(provider.test({}))

        assert success is False
        assert "webhook_url" in message

    def test_test_returns_failure_on_http_error(self, provider) -> None:
        """test() returns failure tuple on HTTP error."""
        import httpx

        with patch.object(
            provider,
            "send",
            new=AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Error", request=MagicMock(), response=MagicMock()
                )
            ),
        ):
            success, message = run_async(
                provider.test({"webhook_url": "https://example.com"})
            )

            assert success is False
            assert "failed" in message.lower()

    def test_test_returns_failure_on_unexpected_error(self, provider) -> None:
        """test() returns failure tuple on unexpected error."""
        with patch.object(
            provider,
            "send",
            new=AsyncMock(side_effect=RuntimeError("Unexpected")),
        ):
            success, message = run_async(
                provider.test({"webhook_url": "https://example.com"})
            )

            assert success is False
            assert "Unexpected" in message
