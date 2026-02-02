"""Tests for taggarr.db.models module."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from taggarr.db.database import create_engine, get_session
from taggarr.db.models import (
    ApiKey,
    Base,
    Config,
    Instance,
    Media,
    Season,
    SessionModel,
    Tag,
    User,
)


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


class TestTagModel:
    """Tests for Tag model."""

    def test_tag_model_create(self, tmp_path: Path) -> None:
        """Tag model should store label."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            tag = Tag(label="dub")
            session.add(tag)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM tags"))
            row = result.fetchone()

            assert row is not None
            assert row.label == "dub"


class TestMediaModel:
    """Tests for Media model."""

    def test_media_model_create(self, tmp_path: Path) -> None:
        """Media model should link to instance and tag."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        added_time = datetime.now(timezone.utc)
        last_scanned = datetime.now(timezone.utc)

        with get_session(engine) as session:
            instance = Instance(
                name="Sonarr Main",
                type="sonarr",
                url="http://localhost:8989",
                api_key="abc123xyz",
                root_path="/media/tv",
                target_languages='["eng", "jpn"]',
                tags='["dub"]',
                quick_mode=0,
                enabled=1,
                require_original_default=0,
                notify_on_wrong_dub=1,
                notify_on_original_missing=0,
            )
            session.add(instance)
            session.flush()

            tag = Tag(label="dub")
            session.add(tag)
            session.flush()

            media = Media(
                instance_id=instance.id,
                path="/media/tv/ShowName",
                title="Show Name",
                clean_title="showname",
                media_type="series",
                original_language="eng",
                tag_id=tag.id,
                added=added_time,
                last_scanned=last_scanned,
                last_modified=1704067200,
                override_require_original=1,
                override_notify=0,
            )
            session.add(media)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM media"))
            row = result.fetchone()

            assert row is not None
            assert row.instance_id == 1
            assert row.path == "/media/tv/ShowName"
            assert row.title == "Show Name"
            assert row.clean_title == "showname"
            assert row.media_type == "series"
            assert row.original_language == "eng"
            assert row.tag_id == 1
            assert row.added is not None
            assert row.last_scanned is not None
            assert row.last_modified == 1704067200
            assert row.override_require_original == 1
            assert row.override_notify == 0


class TestSeasonModel:
    """Tests for Season model."""

    def test_season_model_create(self, tmp_path: Path) -> None:
        """Season model should link to media with episode data."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        added_time = datetime.now(timezone.utc)

        with get_session(engine) as session:
            instance = Instance(
                name="Sonarr Main",
                type="sonarr",
                url="http://localhost:8989",
                api_key="abc123xyz",
                root_path="/media/tv",
                target_languages='["eng", "jpn"]',
                tags='["dub"]',
                quick_mode=0,
                enabled=1,
                require_original_default=0,
                notify_on_wrong_dub=1,
                notify_on_original_missing=0,
            )
            session.add(instance)
            session.flush()

            media = Media(
                instance_id=instance.id,
                path="/media/tv/ShowName",
                title="Show Name",
                clean_title="showname",
                media_type="series",
                added=added_time,
            )
            session.add(media)
            session.flush()

            season = Season(
                media_id=media.id,
                season_number=1,
                episode_count=12,
                status="complete",
                original_dub='["eng"]',
                dub='["eng", "jpn"]',
                missing_dub='["spa"]',
                unexpected_languages='["fra"]',
                last_modified=1704067200,
            )
            session.add(season)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM seasons"))
            row = result.fetchone()

            assert row is not None
            assert row.media_id == 1
            assert row.season_number == 1
            assert row.episode_count == 12
            assert row.status == "complete"
            assert row.original_dub == '["eng"]'
            assert row.dub == '["eng", "jpn"]'
            assert row.missing_dub == '["spa"]'
            assert row.unexpected_languages == '["fra"]'
            assert row.last_modified == 1704067200
