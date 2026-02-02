"""Tests for session token management."""

import datetime

from taggarr.auth.session import (
    create_session_token,
    get_session_expiry,
    is_session_expired,
)


class TestCreateSessionToken:
    """Tests for create_session_token function."""

    def test_create_session_token_returns_token(self) -> None:
        """create_session_token returns a string token."""
        token = create_session_token()

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_session_token_unique(self) -> None:
        """Each call to create_session_token produces a unique token."""
        token1 = create_session_token()
        token2 = create_session_token()

        assert token1 != token2


class TestGetSessionExpiry:
    """Tests for get_session_expiry function."""

    def test_get_session_expiry_returns_future_date(self) -> None:
        """get_session_expiry returns an ISO timestamp in the future."""
        expiry = get_session_expiry()
        now = datetime.datetime.now(datetime.timezone.utc)

        # Parse the ISO timestamp
        expiry_dt = datetime.datetime.fromisoformat(expiry)

        assert expiry_dt > now


class TestIsSessionExpired:
    """Tests for is_session_expired function."""

    def test_is_session_expired_false_for_future(self) -> None:
        """is_session_expired returns False for future timestamps."""
        future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            hours=1
        )
        future_iso = future.isoformat()

        result = is_session_expired(future_iso)

        assert result is False

    def test_is_session_expired_true_for_past(self) -> None:
        """is_session_expired returns True for past timestamps."""
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            hours=1
        )
        past_iso = past.isoformat()

        result = is_session_expired(past_iso)

        assert result is True
