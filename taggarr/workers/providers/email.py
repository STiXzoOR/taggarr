"""Email notification provider."""

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from taggarr.workers.providers.base import NotificationProvider

logger = logging.getLogger("taggarr")


class EmailProvider(NotificationProvider):
    """SMTP email notification provider."""

    async def send(self, title: str, message: str, settings: dict) -> None:
        """Send notification via email.

        Args:
            title: The notification title (used as email subject).
            message: The notification message body.
            settings: Must contain 'smtp_server', 'smtp_port', 'username',
                     'password', 'from_address', 'to_address'.

        Raises:
            ValueError: If required settings are missing.
            smtplib.SMTPException: If sending fails.
        """
        required_fields = [
            "smtp_server",
            "smtp_port",
            "from_address",
            "to_address",
        ]
        for field in required_fields:
            if not settings.get(field):
                raise ValueError(f"Email {field} is required")

        smtp_server = settings["smtp_server"]
        smtp_port = int(settings["smtp_port"])
        username = settings.get("username", "")
        password = settings.get("password", "")
        from_address = settings["from_address"]
        to_address = settings["to_address"]
        use_tls = settings.get("use_tls", True)

        # Create email message
        msg = EmailMessage()
        msg["Subject"] = f"[Taggarr] {title}"
        msg["From"] = from_address
        msg["To"] = to_address
        msg.set_content(message)

        # Send email in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._send_email_sync,
            msg,
            smtp_server,
            smtp_port,
            username,
            password,
            use_tls,
        )

        logger.info(f"Email notification sent to {to_address}: {title}")

    def _send_email_sync(
        self,
        msg: EmailMessage,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        use_tls: bool,
    ) -> None:
        """Synchronous email sending helper.

        Args:
            msg: The email message to send.
            smtp_server: SMTP server hostname.
            smtp_port: SMTP server port.
            username: SMTP username for authentication.
            password: SMTP password for authentication.
            use_tls: Whether to use TLS encryption.
        """
        context = ssl.create_default_context() if use_tls else None

        if smtp_port == 465:
            # SMTPS (implicit TLS)
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
        else:
            # SMTP with optional STARTTLS
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls(context=context)
                if username and password:
                    server.login(username, password)
                server.send_message(msg)

    async def test(self, settings: dict) -> tuple[bool, str]:
        """Test email configuration.

        Args:
            settings: SMTP configuration settings.

        Returns:
            Tuple of (success, message).
        """
        try:
            await self.send(
                title="Taggarr Test Notification",
                message="This is a test notification from Taggarr.",
                settings=settings,
            )
            return True, "Email notification sent successfully"
        except ValueError as e:
            return False, str(e)
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
