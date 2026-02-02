"""Discord notification provider."""

import logging

import httpx

from taggarr.workers.providers.base import NotificationProvider

logger = logging.getLogger("taggarr")


class DiscordProvider(NotificationProvider):
    """Discord webhook notification provider."""

    async def send(self, title: str, message: str, settings: dict) -> None:
        """Send notification via Discord webhook.

        Args:
            title: The notification title.
            message: The notification message body.
            settings: Must contain 'webhook_url'.

        Raises:
            ValueError: If webhook_url is missing.
            httpx.HTTPError: If the request fails.
        """
        webhook_url = settings.get("webhook_url")
        if not webhook_url:
            raise ValueError("Discord webhook_url is required")

        # Build Discord embed
        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": 0x5865F2,  # Discord blurple
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()

        logger.info(f"Discord notification sent: {title}")

    async def test(self, settings: dict) -> tuple[bool, str]:
        """Test Discord webhook configuration.

        Args:
            settings: Must contain 'webhook_url'.

        Returns:
            Tuple of (success, message).
        """
        try:
            await self.send(
                title="Taggarr Test Notification",
                message="This is a test notification from Taggarr.",
                settings=settings,
            )
            return True, "Discord notification sent successfully"
        except ValueError as e:
            return False, str(e)
        except httpx.HTTPError as e:
            return False, f"Discord webhook failed: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
