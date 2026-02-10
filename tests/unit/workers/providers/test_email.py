"""Tests for Email notification provider."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from taggarr.workers.providers.email import EmailProvider


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@pytest.fixture
def provider():
    """Create an EmailProvider instance."""
    return EmailProvider()


@pytest.fixture
def valid_settings():
    """Return valid email settings."""
    return {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "from_address": "test@example.com",
        "to_address": "user@example.com",
        "username": "testuser",
        "password": "testpass",
    }


class TestEmailProviderSend:
    """Tests for EmailProvider.send method."""

    def test_send_requires_smtp_server(self, provider) -> None:
        """send() raises ValueError without smtp_server."""
        with pytest.raises(ValueError, match="smtp_server is required"):
            run_async(
                provider.send(
                    "Title",
                    "Message",
                    {
                        "smtp_port": 587,
                        "from_address": "a@b.com",
                        "to_address": "c@d.com",
                    },
                )
            )

    def test_send_requires_smtp_port(self, provider) -> None:
        """send() raises ValueError without smtp_port."""
        with pytest.raises(ValueError, match="smtp_port is required"):
            run_async(
                provider.send(
                    "Title",
                    "Message",
                    {
                        "smtp_server": "smtp.example.com",
                        "from_address": "a@b.com",
                        "to_address": "c@d.com",
                    },
                )
            )

    def test_send_requires_from_address(self, provider) -> None:
        """send() raises ValueError without from_address."""
        with pytest.raises(ValueError, match="from_address is required"):
            run_async(
                provider.send(
                    "Title",
                    "Message",
                    {
                        "smtp_server": "smtp.example.com",
                        "smtp_port": 587,
                        "to_address": "c@d.com",
                    },
                )
            )

    def test_send_requires_to_address(self, provider) -> None:
        """send() raises ValueError without to_address."""
        with pytest.raises(ValueError, match="to_address is required"):
            run_async(
                provider.send(
                    "Title",
                    "Message",
                    {
                        "smtp_server": "smtp.example.com",
                        "smtp_port": 587,
                        "from_address": "a@b.com",
                    },
                )
            )

    def test_send_uses_starttls_for_port_587(
        self, provider, valid_settings
    ) -> None:
        """send() uses STARTTLS for port 587."""
        with patch("taggarr.workers.providers.email.smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

            run_async(provider.send("Title", "Message", valid_settings))

            mock_smtp.assert_called_once()
            mock_instance.starttls.assert_called_once()
            mock_instance.login.assert_called_once()
            mock_instance.send_message.assert_called_once()

    def test_send_uses_smtps_for_port_465(
        self, provider, valid_settings
    ) -> None:
        """send() uses SMTP_SSL for port 465."""
        valid_settings["smtp_port"] = 465

        with patch("taggarr.workers.providers.email.smtplib.SMTP_SSL") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

            run_async(provider.send("Title", "Message", valid_settings))

            mock_smtp.assert_called_once()


class TestEmailProviderTest:
    """Tests for EmailProvider.test method."""

    def test_test_returns_success_on_success(
        self, provider, valid_settings
    ) -> None:
        """test() returns success tuple on successful send."""
        with patch("taggarr.workers.providers.email.smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

            success, message = run_async(provider.test(valid_settings))

            assert success is True
            assert "successfully" in message

    def test_test_returns_failure_on_missing_settings(self, provider) -> None:
        """test() returns failure tuple on missing settings."""
        success, message = run_async(provider.test({}))

        assert success is False
        assert "required" in message

    def test_test_returns_failure_on_smtp_error(
        self, provider, valid_settings
    ) -> None:
        """test() returns failure tuple on SMTP error."""
        import smtplib

        with patch("taggarr.workers.providers.email.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = MagicMock(
                side_effect=smtplib.SMTPException("Connection failed")
            )
            mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

            success, message = run_async(provider.test(valid_settings))

            assert success is False
            assert "failed" in message.lower()

    def test_test_returns_failure_on_unexpected_error(
        self, provider, valid_settings
    ) -> None:
        """test() returns failure tuple on unexpected error."""
        with patch("taggarr.workers.providers.email.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = MagicMock(
                side_effect=RuntimeError("Unexpected")
            )
            mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

            success, message = run_async(provider.test(valid_settings))

            assert success is False
            assert "Unexpected" in message

    def test_send_skips_login_without_credentials(self, provider) -> None:
        """send() skips login when no username/password provided."""
        settings = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "from_address": "a@b.com",
            "to_address": "c@d.com",
            # No username or password
        }

        with patch("taggarr.workers.providers.email.smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

            run_async(provider.send("Title", "Message", settings))

            mock_instance.login.assert_not_called()
