"""Tests for taggarr.db.models module."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from taggarr.db.database import create_engine, get_session
from taggarr.db.models import ApiKey, Base, SessionModel, User


class TestUserModel:
    """Tests for User model."""

    def test_user_model_create(self, tmp_path: Path) -> None:
        """User model should store username and password hash."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            user = User(
                identifier="550e8400-e29b-41d4-a716-446655440000",
                username="testuser",
                password="hashed_password_value",
                salt="random_salt_value",
                iterations=100000,
            )
            session.add(user)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM users"))
            row = result.fetchone()

            assert row is not None
            assert row.identifier == "550e8400-e29b-41d4-a716-446655440000"
            assert row.username == "testuser"
            assert row.password == "hashed_password_value"
            assert row.salt == "random_salt_value"
            assert row.iterations == 100000


class TestSessionModel:
    """Tests for SessionModel model."""

    def test_session_model_create(self, tmp_path: Path) -> None:
        """Session model should link to user with expiration."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        expires = datetime.now(timezone.utc) + timedelta(hours=24)

        with get_session(engine) as session:
            user = User(
                identifier="550e8400-e29b-41d4-a716-446655440000",
                username="testuser",
                password="hashed_password_value",
                salt="random_salt_value",
                iterations=100000,
            )
            session.add(user)
            session.flush()

            session_model = SessionModel(
                identifier="session_token_abc123",
                user_id=user.id,
                expires_at=expires,
            )
            session.add(session_model)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM sessions"))
            row = result.fetchone()

            assert row is not None
            assert row.identifier == "session_token_abc123"
            assert row.user_id == 1
            assert row.expires_at is not None


class TestApiKeyModel:
    """Tests for ApiKey model."""

    def test_api_key_model_create(self, tmp_path: Path) -> None:
        """ApiKey model should store label and hashed key."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        last_used = datetime.now(timezone.utc)

        with get_session(engine) as session:
            api_key = ApiKey(
                label="My API Key",
                key="hashed_api_key_value",
                last_used_at=last_used,
            )
            session.add(api_key)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM api_keys"))
            row = result.fetchone()

            assert row is not None
            assert row.label == "My API Key"
            assert row.key == "hashed_api_key_value"
            assert row.last_used_at is not None
