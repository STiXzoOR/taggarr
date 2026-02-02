"""Notification providers for taggarr."""

from taggarr.workers.providers.base import NotificationProvider
from taggarr.workers.providers.discord import DiscordProvider
from taggarr.workers.providers.email import EmailProvider
from taggarr.workers.providers.pushover import PushoverProvider
from taggarr.workers.providers.telegram import TelegramProvider
from taggarr.workers.providers.webhook import WebhookProvider

# Provider name to class mapping
PROVIDERS = {
    "discord": DiscordProvider,
    "telegram": TelegramProvider,
    "pushover": PushoverProvider,
    "email": EmailProvider,
    "webhook": WebhookProvider,
}


def get_provider(implementation: str) -> type[NotificationProvider]:
    """Get provider class by implementation name.

    Args:
        implementation: The provider implementation name.

    Returns:
        The provider class.

    Raises:
        ValueError: If the implementation is not supported.
    """
    provider_class = PROVIDERS.get(implementation)
    if not provider_class:
        raise ValueError(f"Unknown notification provider: {implementation}")
    return provider_class


__all__ = [
    "NotificationProvider",
    "DiscordProvider",
    "TelegramProvider",
    "PushoverProvider",
    "EmailProvider",
    "WebhookProvider",
    "PROVIDERS",
    "get_provider",
]
