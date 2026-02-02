"""Session token management for authentication."""

import datetime
import secrets


def create_session_token() -> str:
    """Generate a secure random session token.

    Returns:
        A URL-safe random string token.
    """
    return secrets.token_urlsafe(32)


def get_session_expiry(hours: int = 24) -> str:
    """Get an ISO timestamp for session expiry.

    Args:
        hours: Number of hours until expiry (default 24).

    Returns:
        ISO format timestamp string in UTC.
    """
    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        hours=hours
    )
    return expiry.isoformat()


def is_session_expired(expires_at: str) -> bool:
    """Check if a session has expired.

    Args:
        expires_at: ISO format timestamp string.

    Returns:
        True if the timestamp is in the past, False otherwise.
    """
    expiry_dt = datetime.datetime.fromisoformat(expires_at)
    now = datetime.datetime.now(datetime.timezone.utc)
    return expiry_dt <= now
