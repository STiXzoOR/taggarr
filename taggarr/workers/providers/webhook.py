"""Generic webhook notification provider."""

import logging

import httpx

from taggarr.workers.providers.base import NotificationProvider

logger = logging.getLogger("taggarr")


class WebhookProvider(NotificationProvider):
    """Generic HTTP webhook notification provider."""

    async def send(self, title: str, message: str, settings: dict) -> None:
        """Send notification via generic webhook.

        Args:
            title: The notification title.
            message: The notification message body.
            settings: Must contain 'url'. Optional: 'method' (default POST),
                     'headers' (dict of custom headers).

        Raises:
            ValueError: If url is missing.
            httpx.HTTPError: If the request fails.
        """
        url = settings.get("url")
        if not url:
            raise ValueError("Webhook url is required")

        method = settings.get("method", "POST").upper()
        headers = settings.get("headers", {})

        # Build payload
        payload = {
            "title": title,
            "message": message,
        }

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(
                    url,
                    params=payload,
                    headers=headers,
                    timeout=30.0,
                )
            else:
                response = await client.request(
                    method,
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

            response.raise_for_status()

        logger.info(f"Webhook notification sent to {url}: {title}")

    async def test(self, settings: dict) -> tuple[bool, str]:
        """Test webhook configuration.

        Args:
            settings: Webhook configuration settings.

        Returns:
            Tuple of (success, message).
        """
        try:
            await self.send(
                title="Taggarr Test Notification",
                message="This is a test notification from Taggarr.",
                settings=settings,
            )
            return True, "Webhook notification sent successfully"
        except ValueError as e:
            return False, str(e)
        except httpx.HTTPError as e:
            return False, f"Webhook request failed: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
