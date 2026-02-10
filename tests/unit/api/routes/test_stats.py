"""Tests for stats and system routes."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from taggarr.api.app import create_app
from taggarr.auth import (
    create_session_token,
    get_session_expiry,
    hash_password,
)
from taggarr.db import (
    Backup,
    Base,
    Command,
    History,
    Instance,
    Media,
    SessionModel,
    Tag,
    User,
    init_db,
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite database engine with thread safety."""
    engine = sa_create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    return engine


@pytest.fixture
def db_session(engine):
    """Create a database session."""
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(engine):
    """Create app with database dependency override."""
    from taggarr.api.deps import get_db

    app = create_app()

    def override_get_db():
        session_factory = sessionmaker(bind=engine)
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user in the database."""
    import uuid

    password_hash, salt, iterations = hash_password("testpassword")
    user = User(
        identifier=str(uuid.uuid4()),
        username="testuser",
        password=password_hash,
        salt=salt,
        iterations=iterations,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authenticated_client(client, db_session: Session, test_user):
    """Create a client with an authenticated session."""
    token = create_session_token()
    expires_at = get_session_expiry(hours=24)

    session = SessionModel(
        identifier=token,
        user_id=test_user.id,
        expires_at=datetime.fromisoformat(expires_at),
    )
    db_session.add(session)
    db_session.commit()

    client.cookies.set("session", token)
    return client


def create_instance_in_db(
    db_session: Session,
    **kwargs,
) -> Instance:
    """Helper to create an instance in the database."""
    defaults = {
        "name": "test-sonarr",
        "type": "sonarr",
        "url": "http://localhost:8989",
        "api_key": "test-api-key",
        "root_path": "/media/tv",
        "target_languages": "en,de",
        "tags": "1,2",
        "quick_mode": 0,
        "enabled": 1,
        "require_original_default": 0,
        "notify_on_wrong_dub": 1,
        "notify_on_original_missing": 1,
    }
    defaults.update(kwargs)
    instance = Instance(**defaults)
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


def get_or_create_tag(db_session: Session, label: str) -> Tag:
    """Helper to get or create a tag in the database."""
    tag = db_session.query(Tag).filter(Tag.label == label).first()
    if tag is None:
        tag = Tag(label=label)
        db_session.add(tag)
        db_session.commit()
        db_session.refresh(tag)
    return tag


def create_media_in_db(
    db_session: Session,
    instance: Instance,
    tag: Tag | None = None,
    **kwargs,
) -> Media:
    """Helper to create a media item in the database."""
    defaults = {
        "instance_id": instance.id,
        "path": "/media/tv/show",
        "title": "Test Show",
        "clean_title": "testshow",
        "media_type": "series",
        "added": datetime.now(timezone.utc),
        "tag_id": tag.id if tag else None,
    }
    defaults.update(kwargs)
    media = Media(**defaults)
    db_session.add(media)
    db_session.commit()
    db_session.refresh(media)
    return media


def create_command_in_db(
    db_session: Session,
    status: str = "queued",
    **kwargs,
) -> Command:
    """Helper to create a command in the database."""
    defaults = {
        "name": "ScanLibrary",
        "status": status,
        "queued_at": datetime.now(timezone.utc),
        "trigger": "manual",
    }
    defaults.update(kwargs)
    command = Command(**defaults)
    db_session.add(command)
    db_session.commit()
    db_session.refresh(command)
    return command


def create_history_in_db(
    db_session: Session,
    event_type: str = "scan",
    **kwargs,
) -> History:
    """Helper to create a history entry in the database."""
    defaults = {
        "date": datetime.now(timezone.utc),
        "event_type": event_type,
    }
    defaults.update(kwargs)
    history = History(**defaults)
    db_session.add(history)
    db_session.commit()
    db_session.refresh(history)
    return history


def create_backup_in_db(
    db_session: Session,
    **kwargs,
) -> Backup:
    """Helper to create a backup in the database."""
    defaults = {
        "filename": "taggarr_backup_20240115_120000.zip",
        "path": "/backups/taggarr_backup_20240115_120000.zip",
        "type": "manual",
        "size_bytes": 1024,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    backup = Backup(**defaults)
    db_session.add(backup)
    db_session.commit()
    db_session.refresh(backup)
    return backup


class TestStatsEmptyDatabase:
    """Tests for GET /api/v1/stats with empty database."""

    def test_stats_empty_database(self, authenticated_client) -> None:
        """GET /api/v1/stats returns zeros when database is empty."""
        response = authenticated_client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_media"] == 0
        assert data["total_instances"] == 0
        assert data["media_by_tag"] == {
            "dub": 0,
            "semi-dub": 0,
            "wrong-dub": 0,
            "untagged": 0,
        }
        assert data["recent_scans"] == 0
        assert data["pending_commands"] == 0


class TestStatsWithData:
    """Tests for GET /api/v1/stats with data."""

    def test_stats_with_data(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/stats returns accurate counts."""
        # Create instances
        instance1 = create_instance_in_db(db_session, name="sonarr1")
        instance2 = create_instance_in_db(db_session, name="radarr1", type="radarr")

        # Create tags
        dub_tag = get_or_create_tag(db_session, "dub")
        semi_dub_tag = get_or_create_tag(db_session, "semi-dub")

        # Create media
        create_media_in_db(db_session, instance1, dub_tag, title="Show 1")
        create_media_in_db(db_session, instance1, semi_dub_tag, title="Show 2")
        create_media_in_db(db_session, instance2, None, title="Movie 1")  # untagged

        # Create pending commands
        create_command_in_db(db_session, status="queued")
        create_command_in_db(db_session, status="started")
        create_command_in_db(db_session, status="completed")

        # Create recent scan history (within last 24 hours)
        create_history_in_db(
            db_session,
            event_type="scan",
            date=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        create_history_in_db(
            db_session,
            event_type="scan",
            date=datetime.now(timezone.utc) - timedelta(hours=12),
        )
        # Old scan (more than 24 hours ago)
        create_history_in_db(
            db_session,
            event_type="scan",
            date=datetime.now(timezone.utc) - timedelta(hours=48),
        )

        response = authenticated_client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_media"] == 3
        assert data["total_instances"] == 2
        assert data["recent_scans"] == 2
        # queued and started are pending
        assert data["pending_commands"] == 2


class TestStatsMediaByTag:
    """Tests for media_by_tag grouping in stats."""

    def test_stats_media_by_tag(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/stats correctly groups media by tag."""
        instance = create_instance_in_db(db_session)

        # Create all tag types
        dub_tag = get_or_create_tag(db_session, "dub")
        semi_dub_tag = get_or_create_tag(db_session, "semi-dub")
        wrong_dub_tag = get_or_create_tag(db_session, "wrong-dub")

        # Create media with different tags
        create_media_in_db(db_session, instance, dub_tag, title="Show 1")
        create_media_in_db(db_session, instance, dub_tag, title="Show 2")
        create_media_in_db(db_session, instance, dub_tag, title="Show 3")
        create_media_in_db(db_session, instance, semi_dub_tag, title="Show 4")
        create_media_in_db(db_session, instance, semi_dub_tag, title="Show 5")
        create_media_in_db(db_session, instance, wrong_dub_tag, title="Show 6")
        # Untagged media
        create_media_in_db(db_session, instance, None, title="Show 7")
        create_media_in_db(db_session, instance, None, title="Show 8")
        create_media_in_db(db_session, instance, None, title="Show 9")
        create_media_in_db(db_session, instance, None, title="Show 10")

        response = authenticated_client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["media_by_tag"] == {
            "dub": 3,
            "semi-dub": 2,
            "wrong-dub": 1,
            "untagged": 4,
        }


class TestSystemStatus:
    """Tests for GET /api/v1/system/status endpoint."""

    def test_system_status_returns_version(self, authenticated_client) -> None:
        """GET /api/v1/system/status returns application version."""
        response = authenticated_client.get("/api/v1/system/status")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        # Version should match what's in taggarr.__version__
        from taggarr import __version__

        assert data["version"] == __version__

    def test_system_status_returns_uptime(self, authenticated_client) -> None:
        """GET /api/v1/system/status returns uptime_seconds."""
        response = authenticated_client.get("/api/v1/system/status")

        assert response.status_code == 200
        data = response.json()

        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0

    def test_system_status_returns_database_size(self, authenticated_client) -> None:
        """GET /api/v1/system/status returns database_size_bytes."""
        response = authenticated_client.get("/api/v1/system/status")

        assert response.status_code == 200
        data = response.json()

        assert "database_size_bytes" in data
        assert isinstance(data["database_size_bytes"], int)
        assert data["database_size_bytes"] >= 0

    def test_system_status_returns_last_backup(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/system/status returns last_backup timestamp."""
        # Create a backup
        backup_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        create_backup_in_db(db_session, created_at=backup_time)

        response = authenticated_client.get("/api/v1/system/status")

        assert response.status_code == 200
        data = response.json()

        assert "last_backup" in data
        assert data["last_backup"] is not None
        # Should be an ISO format datetime string
        parsed = datetime.fromisoformat(data["last_backup"].replace("Z", "+00:00"))
        assert parsed.year == 2024
        assert parsed.month == 1
        assert parsed.day == 15

    def test_system_status_last_backup_null_when_no_backups(
        self, authenticated_client
    ) -> None:
        """GET /api/v1/system/status returns null last_backup when no backups exist."""
        response = authenticated_client.get("/api/v1/system/status")

        assert response.status_code == 200
        data = response.json()

        assert data["last_backup"] is None


class TestSystemStatusWithAppState:
    """Tests for system status with startup_time and db_path in app state."""

    def test_system_status_with_startup_time(self, authenticated_client, app) -> None:
        """GET /api/v1/system/status returns nonzero uptime when startup_time is set."""
        app.state.startup_time = datetime.now(timezone.utc) - timedelta(seconds=120)

        response = authenticated_client.get("/api/v1/system/status")

        assert response.status_code == 200
        data = response.json()
        assert data["uptime_seconds"] >= 119  # Allow 1s tolerance

    def test_system_status_with_db_path(self, authenticated_client, app, tmp_path) -> None:
        """GET /api/v1/system/status returns database size when db_path is set."""
        db_file = tmp_path / "test.db"
        db_file.write_bytes(b"x" * 4096)
        app.state.db_path = str(db_file)

        response = authenticated_client.get("/api/v1/system/status")

        assert response.status_code == 200
        data = response.json()
        assert data["database_size_bytes"] == 4096


class TestStatsRoutesRequireAuth:
    """Tests for authentication requirement on stats routes."""

    def test_stats_routes_require_auth(self, client) -> None:
        """All stats endpoints return 401 without authentication."""
        # GET /api/v1/stats
        response = client.get("/api/v1/stats")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/system/status
        response = client.get("/api/v1/system/status")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
