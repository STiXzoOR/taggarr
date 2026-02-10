"""Base notification provider interface."""

from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    @abstractmethod
    async def send(self, title: str, message: str, settings: dict) -> None:
        """Send a notification.

        Args:
            title: The notification title.
            message: The notification message body.
            settings: Provider-specific settings dictionary.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
            Exception: If sending fails.
        """
        raise NotImplementedError

    @abstractmethod
    async def test(self, settings: dict) -> tuple[bool, str]:
        """Test the notification configuration.

        Args:
            settings: Provider-specific settings dictionary.

        Returns:
            Tuple of (success, message).
        """
        raise NotImplementedError
