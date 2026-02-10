"""Tests for history routes."""

import json
from datetime import datetime

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
from taggarr.db import Base, History, Instance, Media, SessionModel, User, init_db


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


@pytest.fixture
def sample_instance(db_session: Session) -> Instance:
    """Create a sample instance in the database."""
    instance = Instance(
        name="test-sonarr",
        type="sonarr",
        url="http://localhost:8989",
        api_key="test-key",
        root_path="/media/tv",
        target_languages=json.dumps(["en", "de"]),
        tags=json.dumps(["dub", "semi-dub"]),
        target_genre=None,
        quick_mode=0,
        enabled=1,
        require_original_default=1,
        notify_on_wrong_dub=1,
        notify_on_original_missing=0,
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


def create_media_in_db(
    db_session: Session,
    instance: Instance,
    **kwargs,
) -> Media:
    """Helper to create media in the database."""
    defaults = {
        "instance_id": instance.id,
        "path": "/media/tv/TestShow",
        "title": "Test Show",
        "clean_title": "testshow",
        "media_type": "series",
        "original_language": "en",
        "tag_id": None,
        "added": datetime.now(),
        "last_scanned": None,
        "last_modified": None,
        "override_require_original": None,
        "override_notify": None,
    }
    defaults.update(kwargs)
    media = Media(**defaults)
    db_session.add(media)
    db_session.commit()
    db_session.refresh(media)
    return media


def create_history_in_db(
    db_session: Session,
    media: Media | None = None,
    instance: Instance | None = None,
    **kwargs,
) -> History:
    """Helper to create a history entry in the database."""
    defaults = {
        "date": datetime.now(),
        "event_type": "scan",
        "media_id": media.id if media else None,
        "instance_id": instance.id if instance else None,
        "data": json.dumps({"detail": "test"}),
    }
    defaults.update(kwargs)
    history = History(**defaults)
    db_session.add(history)
    db_session.commit()
    db_session.refresh(history)
    return history


class TestListHistory:
    """Tests for GET /api/v1/history endpoint."""

    def test_list_history_empty(self, authenticated_client) -> None:
        """GET /api/v1/history returns empty list with pagination when no history exists."""
        response = authenticated_client.get("/api/v1/history")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 25

    def test_list_history_paginated(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/history returns paginated results."""
        media = create_media_in_db(db_session, sample_instance)

        # Create 30 history entries
        for i in range(30):
            create_history_in_db(
                db_session,
                media=media,
                event_type=f"event_{i}",
            )

        # First page
        response = authenticated_client.get("/api/v1/history?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 30
        assert data["page"] == 1
        assert data["page_size"] == 10

        # Second page
        response = authenticated_client.get("/api/v1/history?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 2

        # Third page
        response = authenticated_client.get("/api/v1/history?page=3&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 3

    def test_list_history_filter_by_media(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/history filters by media_id."""
        media1 = create_media_in_db(
            db_session,
            sample_instance,
            title="Show 1",
            path="/media/tv/Show1",
            clean_title="show1",
        )
        media2 = create_media_in_db(
            db_session,
            sample_instance,
            title="Show 2",
            path="/media/tv/Show2",
            clean_title="show2",
        )

        # Create history for each media
        create_history_in_db(db_session, media=media1, event_type="scan_media1")
        create_history_in_db(db_session, media=media1, event_type="tag_media1")
        create_history_in_db(db_session, media=media2, event_type="scan_media2")
        # Create history without media
        create_history_in_db(db_session, instance=sample_instance, event_type="global_event")

        # Filter by first media
        response = authenticated_client.get(f"/api/v1/history?media_id={media1.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        event_types = {h["event_type"] for h in data["items"]}
        assert event_types == {"scan_media1", "tag_media1"}

        # Filter by second media
        response = authenticated_client.get(f"/api/v1/history?media_id={media2.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["event_type"] == "scan_media2"

    def test_list_history_filter_by_event(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/history filters by event type."""
        media = create_media_in_db(db_session, sample_instance)

        # Create different event types
        create_history_in_db(db_session, media=media, event_type="scan")
        create_history_in_db(db_session, media=media, event_type="scan")
        create_history_in_db(db_session, media=media, event_type="tag_updated")
        create_history_in_db(db_session, instance=sample_instance, event_type="instance_created")

        # Filter by scan event type
        response = authenticated_client.get("/api/v1/history?event=scan")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert all(h["event_type"] == "scan" for h in data["items"])

        # Filter by tag_updated event type
        response = authenticated_client.get("/api/v1/history?event=tag_updated")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["event_type"] == "tag_updated"

    def test_list_history_page_size_max(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/history enforces max page_size of 100."""
        media = create_media_in_db(db_session, sample_instance)

        # Create 150 history entries
        for i in range(150):
            create_history_in_db(db_session, media=media, event_type=f"event_{i}")

        # Request page_size > 100
        response = authenticated_client.get("/api/v1/history?page_size=200")
        assert response.status_code == 200
        data = response.json()
        # Should be capped at 100
        assert len(data["items"]) == 100
        assert data["page_size"] == 100

    def test_list_history_includes_media_title(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/history includes media title for display."""
        media = create_media_in_db(
            db_session,
            sample_instance,
            title="Breaking Bad",
        )
        create_history_in_db(db_session, media=media, event_type="scan")

        response = authenticated_client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["media_title"] == "Breaking Bad"

    def test_list_history_media_title_null_when_no_media(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/history returns null media_title when history has no media."""
        create_history_in_db(db_session, instance=sample_instance, event_type="global_event")

        response = authenticated_client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["media_title"] is None


class TestHistoryValidatorEdgeCases:
    """Tests for validator edge cases in response models."""

    def test_history_list_item_with_null_data(self) -> None:
        """HistoryListItem handles null data field."""
        from taggarr.api.routes.history import HistoryListItem

        response = HistoryListItem(
            id=1,
            date=datetime.now(),
            event_type="scan",
            media_id=1,
            media_title="Test Show",
            instance_id=1,
            data=None,  # Null data
        )

        assert response.data is None

    def test_history_list_item_with_dict_data(self) -> None:
        """HistoryListItem handles data that is already a dict (not JSON string)."""
        from taggarr.api.routes.history import HistoryListItem

        response = HistoryListItem(
            id=1,
            date=datetime.now(),
            event_type="tag_updated",
            media_id=1,
            media_title="Test Show",
            instance_id=None,
            data={"old_tag": "dub", "new_tag": "semi-dub"},  # Already a dict
        )

        assert response.data == {"old_tag": "dub", "new_tag": "semi-dub"}


class TestHistoryAuthRequired:
    """Tests for authentication requirement on history routes."""

    def test_history_routes_require_auth(self, client) -> None:
        """All history endpoints return 401 without authentication."""
        # GET /api/v1/history
        response = client.get("/api/v1/history")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
