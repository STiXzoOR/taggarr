"""Tests for Webhook notification provider."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taggarr.workers.providers.webhook import WebhookProvider


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@pytest.fixture
def provider():
    """Create a WebhookProvider instance."""
    return WebhookProvider()


class TestWebhookProviderSend:
    """Tests for WebhookProvider.send method."""

    def test_send_requires_url(self, provider) -> None:
        """send() raises ValueError without url."""
        with pytest.raises(ValueError, match="url is required"):
            run_async(provider.send("Title", "Message", {}))

    def test_send_posts_to_url(self, provider) -> None:
        """send() posts JSON to webhook URL by default."""
        with patch("taggarr.workers.providers.webhook.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            run_async(
                provider.send(
                    "Test Title",
                    "Test Message",
                    {"url": "https://example.com/webhook"},
                )
            )

            mock_instance.request.assert_called_once()
            call_args = mock_instance.request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "https://example.com/webhook"
            payload = call_args[1]["json"]
            assert payload["title"] == "Test Title"
            assert payload["message"] == "Test Message"

    def test_send_uses_get_method(self, provider) -> None:
        """send() uses GET method when specified."""
        with patch("taggarr.workers.providers.webhook.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            run_async(
                provider.send(
                    "Test Title",
                    "Test Message",
                    {"url": "https://example.com/webhook", "method": "GET"},
                )
            )

            mock_instance.get.assert_called_once()

    def test_send_includes_custom_headers(self, provider) -> None:
        """send() includes custom headers in request."""
        with patch("taggarr.workers.providers.webhook.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            run_async(
                provider.send(
                    "Title",
                    "Message",
                    {
                        "url": "https://example.com/webhook",
                        "headers": {"X-Custom": "value"},
                    },
                )
            )

            call_args = mock_instance.request.call_args
            assert call_args[1]["headers"] == {"X-Custom": "value"}


class TestWebhookProviderTest:
    """Tests for WebhookProvider.test method."""

    def test_test_returns_success_on_success(self, provider) -> None:
        """test() returns success tuple on successful send."""
        with patch.object(provider, "send", new=AsyncMock(return_value=None)):
            success, message = run_async(
                provider.test({"url": "https://example.com"})
            )

            assert success is True
            assert "successfully" in message

    def test_test_returns_failure_on_missing_url(self, provider) -> None:
        """test() returns failure tuple on missing URL."""
        success, message = run_async(provider.test({}))

        assert success is False
        assert "url" in message

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
                provider.test({"url": "https://example.com"})
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
                provider.test({"url": "https://example.com"})
            )

            assert success is False
            assert "Unexpected" in message
