"""Pushover notification provider."""

import logging

import httpx

from taggarr.workers.providers.base import NotificationProvider

logger = logging.getLogger("taggarr")


class PushoverProvider(NotificationProvider):
    """Pushover notification provider."""

    PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"

    async def send(self, title: str, message: str, settings: dict) -> None:
        """Send notification via Pushover API.

        Args:
            title: The notification title.
            message: The notification message body.
            settings: Must contain 'user_key' and 'api_token'.

        Raises:
            ValueError: If required settings are missing.
            httpx.HTTPError: If the request fails.
        """
        user_key = settings.get("user_key")
        api_token = settings.get("api_token")

        if not user_key:
            raise ValueError("Pushover user_key is required")
        if not api_token:
            raise ValueError("Pushover api_token is required")

        payload = {
            "token": api_token,
            "user": user_key,
            "title": title,
            "message": message,
        }

        # Optional priority setting
        if "priority" in settings:
            payload["priority"] = settings["priority"]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.PUSHOVER_API_URL,
                data=payload,
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") != 1:
                errors = data.get("errors", ["Unknown error"])
                raise ValueError(f"Pushover API error: {', '.join(errors)}")

        logger.info(f"Pushover notification sent: {title}")

    async def test(self, settings: dict) -> tuple[bool, str]:
        """Test Pushover configuration.

        Args:
            settings: Must contain 'user_key' and 'api_token'.

        Returns:
            Tuple of (success, message).
        """
        try:
            await self.send(
                title="Taggarr Test Notification",
                message="This is a test notification from Taggarr.",
                settings=settings,
            )
            return True, "Pushover notification sent successfully"
        except ValueError as e:
            return False, str(e)
        except httpx.HTTPError as e:
            return False, f"Pushover API failed: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
