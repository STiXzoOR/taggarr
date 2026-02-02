"""Tests for taggarr.db.models module."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from taggarr.db.database import create_engine, get_session
from taggarr.db.models import ApiKey, Base, Config, Instance, SessionModel, User


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


class TestConfigModel:
    """Tests for Config model."""

    def test_config_model_key_value(self, tmp_path: Path) -> None:
        """Config model should store key-value pairs."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            config = Config(
                key="app_version",
                value="1.0.0",
            )
            session.add(config)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM config"))
            row = result.fetchone()

            assert row is not None
            assert row.key == "app_version"
            assert row.value == "1.0.0"

    def test_config_key_unique(self, tmp_path: Path) -> None:
        """Config keys must be unique."""
        import pytest
        from sqlalchemy.exc import IntegrityError

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            config1 = Config(key="duplicate_key", value="value1")
            session.add(config1)

        with pytest.raises(IntegrityError):
            with get_session(engine) as session:
                config2 = Config(key="duplicate_key", value="value2")
                session.add(config2)


class TestInstanceModel:
    """Tests for Instance model."""

    def test_instance_model_create(self, tmp_path: Path) -> None:
        """Instance model should store Sonarr/Radarr connection info."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            instance = Instance(
                name="Sonarr Main",
                type="sonarr",
                url="http://localhost:8989",
                api_key="abc123xyz",
                root_path="/media/tv",
                target_languages='["eng", "jpn"]',
                tags='["dub", "anime"]',
                target_genre="Anime",
                quick_mode=1,
                enabled=1,
                require_original_default=0,
                notify_on_wrong_dub=1,
                notify_on_original_missing=0,
            )
            session.add(instance)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM instances"))
            row = result.fetchone()

            assert row is not None
            assert row.name == "Sonarr Main"
            assert row.type == "sonarr"
            assert row.url == "http://localhost:8989"
            assert row.api_key == "abc123xyz"
            assert row.root_path == "/media/tv"
            assert row.target_languages == '["eng", "jpn"]'
            assert row.tags == '["dub", "anime"]'
            assert row.target_genre == "Anime"
            assert row.quick_mode == 1
            assert row.enabled == 1
            assert row.require_original_default == 0
            assert row.notify_on_wrong_dub == 1
            assert row.notify_on_original_missing == 0
