"""Tests for taggarr.workers.providers module."""

import pytest

from taggarr.workers.providers import get_provider, PROVIDERS
from taggarr.workers.providers.discord import DiscordProvider
from taggarr.workers.providers.webhook import WebhookProvider


class TestGetProvider:
    """Tests for get_provider function."""

    def test_returns_known_provider(self) -> None:
        """get_provider returns correct class for known implementations."""
        assert get_provider("discord") is DiscordProvider
        assert get_provider("webhook") is WebhookProvider

    def test_raises_for_unknown_provider(self) -> None:
        """get_provider raises ValueError for unknown implementation."""
        with pytest.raises(ValueError, match="Unknown notification provider"):
            get_provider("nonexistent")

    def test_all_providers_registered(self) -> None:
        """All expected providers are registered in PROVIDERS."""
        expected = {"discord", "telegram", "pushover", "email", "webhook"}
        assert set(PROVIDERS.keys()) == expected
