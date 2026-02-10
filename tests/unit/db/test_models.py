"""Tests for taggarr.db.models module."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from taggarr.db.database import create_engine, get_session
from taggarr.db.models import (
    ApiKey,
    Backup,
    Base,
    Command,
    Config,
    History,
    Instance,
    Media,
    Notification,
    NotificationStatus,
    ScheduledTask,
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


class TestHistoryModel:
    """Tests for History model."""

    def test_history_model_create(self, tmp_path: Path) -> None:
        """History model should store events with flexible data."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        event_time = datetime.now(timezone.utc)

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
                added=event_time,
            )
            session.add(media)
            session.flush()

            history = History(
                date=event_time,
                event_type="scan_completed",
                media_id=media.id,
                instance_id=instance.id,
                data='{"episodes_scanned": 12, "tags_updated": true}',
            )
            session.add(history)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM history"))
            row = result.fetchone()

            assert row is not None
            assert row.date is not None
            assert row.event_type == "scan_completed"
            assert row.media_id == 1
            assert row.instance_id == 1
            assert row.data == '{"episodes_scanned": 12, "tags_updated": true}'

    def test_history_model_optional_fields(self, tmp_path: Path) -> None:
        """History model should allow null media_id, instance_id, and data."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        event_time = datetime.now(timezone.utc)

        with get_session(engine) as session:
            history = History(
                date=event_time,
                event_type="application_started",
            )
            session.add(history)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM history"))
            row = result.fetchone()

            assert row is not None
            assert row.event_type == "application_started"
            assert row.media_id is None
            assert row.instance_id is None
            assert row.data is None


class TestNotificationModel:
    """Tests for Notification model."""

    def test_notification_model_create(self, tmp_path: Path) -> None:
        """Notification model should store provider config and triggers."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            notification = Notification(
                name="Discord Alerts",
                implementation="discord",
                settings='{"webhook_url": "https://discord.com/api/webhooks/123"}',
                on_scan_completed=0,
                on_wrong_dub_detected=1,
                on_original_missing=1,
                on_health_issue=0,
                on_application_update=0,
                include_health_warnings=0,
                tags='[1, 2]',
            )
            session.add(notification)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM notifications"))
            row = result.fetchone()

            assert row is not None
            assert row.name == "Discord Alerts"
            assert row.implementation == "discord"
            assert (
                row.settings
                == '{"webhook_url": "https://discord.com/api/webhooks/123"}'
            )
            assert row.on_scan_completed == 0
            assert row.on_wrong_dub_detected == 1
            assert row.on_original_missing == 1
            assert row.on_health_issue == 0
            assert row.on_application_update == 0
            assert row.include_health_warnings == 0
            assert row.tags == '[1, 2]'

    def test_notification_model_defaults(self, tmp_path: Path) -> None:
        """Notification model should use default values for trigger fields."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            notification = Notification(
                name="Email Alerts",
                implementation="email",
                settings='{"smtp_host": "smtp.example.com"}',
            )
            session.add(notification)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM notifications"))
            row = result.fetchone()

            assert row is not None
            assert row.on_scan_completed == 0
            assert row.on_wrong_dub_detected == 1
            assert row.on_original_missing == 1
            assert row.on_health_issue == 0
            assert row.on_application_update == 0
            assert row.include_health_warnings == 0
            assert row.tags is None


class TestNotificationStatusModel:
    """Tests for NotificationStatus model."""

    def test_notification_status_model_create(self, tmp_path: Path) -> None:
        """NotificationStatus model should track notification delivery status."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        last_sent = datetime.now(timezone.utc)

        with get_session(engine) as session:
            notification = Notification(
                name="Slack Alerts",
                implementation="slack",
                settings='{"webhook_url": "https://hooks.slack.com/..."}',
            )
            session.add(notification)
            session.flush()

            status = NotificationStatus(
                notification_id=notification.id,
                last_sent_at=last_sent,
                last_error=None,
                consecutive_failures=0,
            )
            session.add(status)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM notification_status"))
            row = result.fetchone()

            assert row is not None
            assert row.notification_id == 1
            assert row.last_sent_at is not None
            assert row.last_error is None
            assert row.consecutive_failures == 0

    def test_notification_status_with_error(self, tmp_path: Path) -> None:
        """NotificationStatus should store error details and failure count."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            notification = Notification(
                name="Webhook",
                implementation="webhook",
                settings='{"url": "https://example.com/hook"}',
            )
            session.add(notification)
            session.flush()

            status = NotificationStatus(
                notification_id=notification.id,
                last_error="Connection timeout after 30s",
                consecutive_failures=3,
            )
            session.add(status)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM notification_status"))
            row = result.fetchone()

            assert row is not None
            assert row.last_sent_at is None
            assert row.last_error == "Connection timeout after 30s"
            assert row.consecutive_failures == 3

    def test_notification_status_unique_notification_id(self, tmp_path: Path) -> None:
        """NotificationStatus notification_id must be unique."""
        import pytest
        from sqlalchemy.exc import IntegrityError

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            notification = Notification(
                name="Test",
                implementation="test",
                settings="{}",
            )
            session.add(notification)
            session.flush()

            status1 = NotificationStatus(
                notification_id=notification.id,
                consecutive_failures=0,
            )
            session.add(status1)

        with pytest.raises(IntegrityError):
            with get_session(engine) as session:
                status2 = NotificationStatus(
                    notification_id=1,
                    consecutive_failures=0,
                )
                session.add(status2)


class TestCommandModel:
    """Tests for Command model."""

    def test_command_model_create(self, tmp_path: Path) -> None:
        """Command model should store async command queue."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        queued_time = datetime.now(timezone.utc)
        started_time = datetime.now(timezone.utc)
        ended_time = datetime.now(timezone.utc)

        with get_session(engine) as session:
            command = Command(
                name="scan_library",
                body='{"instance_id": 1, "force": true}',
                status="completed",
                queued_at=queued_time,
                started_at=started_time,
                ended_at=ended_time,
                duration="00:05:32",
                exception=None,
                trigger="manual",
            )
            session.add(command)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM commands"))
            row = result.fetchone()

            assert row is not None
            assert row.name == "scan_library"
            assert row.body == '{"instance_id": 1, "force": true}'
            assert row.status == "completed"
            assert row.queued_at is not None
            assert row.started_at is not None
            assert row.ended_at is not None
            assert row.duration == "00:05:32"
            assert row.exception is None
            assert row.trigger == "manual"

    def test_command_model_optional_fields(self, tmp_path: Path) -> None:
        """Command model should allow null optional fields."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        queued_time = datetime.now(timezone.utc)

        with get_session(engine) as session:
            command = Command(
                name="refresh_series",
                status="queued",
                queued_at=queued_time,
                trigger="scheduled",
            )
            session.add(command)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM commands"))
            row = result.fetchone()

            assert row is not None
            assert row.name == "refresh_series"
            assert row.body is None
            assert row.status == "queued"
            assert row.started_at is None
            assert row.ended_at is None
            assert row.duration is None
            assert row.exception is None

    def test_command_model_with_exception(self, tmp_path: Path) -> None:
        """Command model should store exception details on failure."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        queued_time = datetime.now(timezone.utc)
        started_time = datetime.now(timezone.utc)
        ended_time = datetime.now(timezone.utc)

        with get_session(engine) as session:
            command = Command(
                name="scan_library",
                status="failed",
                queued_at=queued_time,
                started_at=started_time,
                ended_at=ended_time,
                duration="00:00:05",
                exception="ConnectionError: Unable to reach Sonarr API",
                trigger="api",
            )
            session.add(command)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM commands"))
            row = result.fetchone()

            assert row is not None
            assert row.status == "failed"
            assert row.exception == "ConnectionError: Unable to reach Sonarr API"


class TestScheduledTaskModel:
    """Tests for ScheduledTask model."""

    def test_scheduled_task_model_create(self, tmp_path: Path) -> None:
        """ScheduledTask model should track recurring jobs."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        last_exec = datetime.now(timezone.utc)
        last_start = datetime.now(timezone.utc)

        with get_session(engine) as session:
            task = ScheduledTask(
                type_name="library_scan",
                last_execution=last_exec,
                last_start_time=last_start,
                interval=3600,
            )
            session.add(task)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM scheduled_tasks"))
            row = result.fetchone()

            assert row is not None
            assert row.type_name == "library_scan"
            assert row.last_execution is not None
            assert row.last_start_time is not None
            assert row.interval == 3600

    def test_scheduled_task_model_optional_fields(self, tmp_path: Path) -> None:
        """ScheduledTask model should allow null execution times."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            task = ScheduledTask(
                type_name="backup_database",
                interval=86400,
            )
            session.add(task)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM scheduled_tasks"))
            row = result.fetchone()

            assert row is not None
            assert row.type_name == "backup_database"
            assert row.last_execution is None
            assert row.last_start_time is None
            assert row.interval == 86400

    def test_scheduled_task_type_name_unique(self, tmp_path: Path) -> None:
        """ScheduledTask type_name must be unique."""
        import pytest
        from sqlalchemy.exc import IntegrityError

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        with get_session(engine) as session:
            task1 = ScheduledTask(
                type_name="library_scan",
                interval=3600,
            )
            session.add(task1)

        with pytest.raises(IntegrityError):
            with get_session(engine) as session:
                task2 = ScheduledTask(
                    type_name="library_scan",
                    interval=7200,
                )
                session.add(task2)


class TestBackupModel:
    """Tests for Backup model."""

    def test_backup_model_create(self, tmp_path: Path) -> None:
        """Backup model should store backup metadata."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        created_time = datetime.now(timezone.utc)

        with get_session(engine) as session:
            backup = Backup(
                filename="taggarr_backup_20240101_120000.zip",
                path="/backups/taggarr_backup_20240101_120000.zip",
                type="scheduled",
                size_bytes=1048576,
                created_at=created_time,
            )
            session.add(backup)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM backups"))
            row = result.fetchone()

            assert row is not None
            assert row.filename == "taggarr_backup_20240101_120000.zip"
            assert row.path == "/backups/taggarr_backup_20240101_120000.zip"
            assert row.type == "scheduled"
            assert row.size_bytes == 1048576
            assert row.created_at is not None

    def test_backup_model_optional_size(self, tmp_path: Path) -> None:
        """Backup model should allow null size_bytes."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)

        created_time = datetime.now(timezone.utc)

        with get_session(engine) as session:
            backup = Backup(
                filename="taggarr_backup_manual.zip",
                path="/backups/taggarr_backup_manual.zip",
                type="manual",
                created_at=created_time,
            )
            session.add(backup)

        with get_session(engine) as session:
            result = session.execute(text("SELECT * FROM backups"))
            row = result.fetchone()

            assert row is not None
            assert row.filename == "taggarr_backup_manual.zip"
            assert row.type == "manual"
            assert row.size_bytes is None
