"""Telegram notification provider."""

import logging

import httpx

from taggarr.workers.providers.base import NotificationProvider

logger = logging.getLogger("taggarr")


class TelegramProvider(NotificationProvider):
    """Telegram Bot API notification provider."""

    TELEGRAM_API_BASE = "https://api.telegram.org"

    async def send(self, title: str, message: str, settings: dict) -> None:
        """Send notification via Telegram Bot API.

        Args:
            title: The notification title.
            message: The notification message body.
            settings: Must contain 'bot_token' and 'chat_id'.

        Raises:
            ValueError: If required settings are missing.
            httpx.HTTPError: If the request fails.
        """
        bot_token = settings.get("bot_token")
        chat_id = settings.get("chat_id")

        if not bot_token:
            raise ValueError("Telegram bot_token is required")
        if not chat_id:
            raise ValueError("Telegram chat_id is required")

        # Format message with title
        text = f"*{title}*\n\n{message}"

        url = f"{self.TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("ok"):
                raise ValueError(f"Telegram API error: {data.get('description')}")

        logger.info(f"Telegram notification sent: {title}")

    async def test(self, settings: dict) -> tuple[bool, str]:
        """Test Telegram bot configuration.

        Args:
            settings: Must contain 'bot_token' and 'chat_id'.

        Returns:
            Tuple of (success, message).
        """
        try:
            await self.send(
                title="Taggarr Test Notification",
                message="This is a test notification from Taggarr.",
                settings=settings,
            )
            return True, "Telegram notification sent successfully"
        except ValueError as e:
            return False, str(e)
        except httpx.HTTPError as e:
            return False, f"Telegram API failed: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
