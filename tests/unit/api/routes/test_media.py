"""Tests for media routes."""

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
from taggarr.db import Base, History, Instance, Media, Season, SessionModel, Tag, User, init_db


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


@pytest.fixture
def sample_tag(db_session: Session) -> Tag:
    """Create or get a sample tag in the database."""
    existing = db_session.query(Tag).filter(Tag.label == "dub").first()
    if existing:
        return existing
    tag = Tag(label="dub")
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
    """Helper to create media in the database."""
    defaults = {
        "instance_id": instance.id,
        "path": "/media/tv/TestShow",
        "title": "Test Show",
        "clean_title": "testshow",
        "media_type": "series",
        "original_language": "en",
        "tag_id": tag.id if tag else None,
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


def create_season_in_db(
    db_session: Session,
    media: Media,
    **kwargs,
) -> Season:
    """Helper to create a season in the database."""
    defaults = {
        "media_id": media.id,
        "season_number": 1,
        "episode_count": 10,
        "status": "complete",
        "original_dub": json.dumps(["en"]),
        "dub": json.dumps(["en", "de"]),
        "missing_dub": None,
        "unexpected_languages": None,
        "last_modified": None,
    }
    defaults.update(kwargs)
    season = Season(**defaults)
    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)
    return season


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


class TestListMedia:
    """Tests for GET /api/v1/media endpoint."""

    def test_list_media_empty(self, authenticated_client) -> None:
        """GET /api/v1/media returns empty list with pagination when no media exists."""
        response = authenticated_client.get("/api/v1/media")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 25

    def test_list_media_paginated(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/media returns paginated results."""
        # Create 30 media items
        for i in range(30):
            create_media_in_db(
                db_session,
                sample_instance,
                title=f"Show {i}",
                path=f"/media/tv/Show{i}",
                clean_title=f"show{i}",
            )

        # First page
        response = authenticated_client.get("/api/v1/media?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 30
        assert data["page"] == 1
        assert data["page_size"] == 10

        # Second page
        response = authenticated_client.get("/api/v1/media?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 2

        # Third page
        response = authenticated_client.get("/api/v1/media?page=3&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 3

    def test_list_media_filter_by_instance(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/media filters by instance_id."""
        # Create another instance
        instance2 = Instance(
            name="radarr-main",
            type="radarr",
            url="http://localhost:7878",
            api_key="test-key-2",
            root_path="/media/movies",
            target_languages=json.dumps(["en"]),
            tags=json.dumps(["dub"]),
            quick_mode=0,
            enabled=1,
            require_original_default=1,
            notify_on_wrong_dub=1,
            notify_on_original_missing=0,
        )
        db_session.add(instance2)
        db_session.commit()
        db_session.refresh(instance2)

        # Create media for each instance
        create_media_in_db(db_session, sample_instance, title="Sonarr Show")
        create_media_in_db(db_session, instance2, title="Radarr Movie", media_type="movie")

        # Filter by first instance
        response = authenticated_client.get(f"/api/v1/media?instance_id={sample_instance.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Sonarr Show"

        # Filter by second instance
        response = authenticated_client.get(f"/api/v1/media?instance_id={instance2.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Radarr Movie"

    def test_list_media_filter_by_tag(
        self,
        authenticated_client,
        db_session: Session,
        sample_instance: Instance,
        sample_tag: Tag,
    ) -> None:
        """GET /api/v1/media filters by tag_id."""
        # Create another tag (check if exists first)
        tag2 = db_session.query(Tag).filter(Tag.label == "semi-dub").first()
        if not tag2:
            tag2 = Tag(label="semi-dub")
            db_session.add(tag2)
            db_session.commit()
            db_session.refresh(tag2)

        # Create media with different tags
        create_media_in_db(db_session, sample_instance, tag=sample_tag, title="Dubbed Show")
        create_media_in_db(db_session, sample_instance, tag=tag2, title="Semi-dubbed Show")
        create_media_in_db(db_session, sample_instance, title="No Tag Show")

        # Filter by dub tag
        response = authenticated_client.get(f"/api/v1/media?tag_id={sample_tag.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Dubbed Show"

        # Filter by semi-dub tag
        response = authenticated_client.get(f"/api/v1/media?tag_id={tag2.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Semi-dubbed Show"

    def test_list_media_search(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/media filters by title search."""
        create_media_in_db(db_session, sample_instance, title="Breaking Bad")
        create_media_in_db(db_session, sample_instance, title="Better Call Saul")
        create_media_in_db(db_session, sample_instance, title="The Office")

        # Search for "Breaking"
        response = authenticated_client.get("/api/v1/media?search=Breaking")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Breaking Bad"

        # Search for "Call" (case insensitive)
        response = authenticated_client.get("/api/v1/media?search=call")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Better Call Saul"

    def test_list_media_page_size_max(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/media enforces max page_size of 100."""
        # Create 150 media items
        for i in range(150):
            create_media_in_db(
                db_session,
                sample_instance,
                title=f"Show {i}",
                path=f"/media/tv/Show{i}",
                clean_title=f"show{i}",
            )

        # Request page_size > 100
        response = authenticated_client.get("/api/v1/media?page_size=200")
        assert response.status_code == 200
        data = response.json()
        # Should be capped at 100
        assert len(data["items"]) == 100
        assert data["page_size"] == 100


class TestGetMedia:
    """Tests for GET /api/v1/media/{id} endpoint."""

    def test_get_media_success(
        self,
        authenticated_client,
        db_session: Session,
        sample_instance: Instance,
        sample_tag: Tag,
    ) -> None:
        """GET /api/v1/media/{id} returns media with seasons."""
        media = create_media_in_db(
            db_session,
            sample_instance,
            tag=sample_tag,
            title="Test Series",
        )
        create_season_in_db(db_session, media, season_number=1, episode_count=10)
        create_season_in_db(db_session, media, season_number=2, episode_count=8)

        response = authenticated_client.get(f"/api/v1/media/{media.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == media.id
        assert data["title"] == "Test Series"
        assert data["instance_name"] == "test-sonarr"
        assert data["tag_label"] == "dub"
        assert len(data["seasons"]) == 2
        assert data["seasons"][0]["season_number"] == 1
        assert data["seasons"][0]["episode_count"] == 10
        assert data["seasons"][1]["season_number"] == 2
        assert data["seasons"][1]["episode_count"] == 8

    def test_get_media_not_found(self, authenticated_client) -> None:
        """GET /api/v1/media/{id} returns 404 for non-existent media."""
        response = authenticated_client.get("/api/v1/media/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Media not found"


class TestUpdateMedia:
    """Tests for PUT /api/v1/media/{id} endpoint."""

    def test_update_media_overrides(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """PUT /api/v1/media/{id} updates overrides."""
        media = create_media_in_db(db_session, sample_instance)

        response = authenticated_client.put(
            f"/api/v1/media/{media.id}",
            json={
                "override_require_original": True,
                "override_notify": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["override_require_original"] is True
        assert data["override_notify"] is False

        # Verify in database
        db_session.expire_all()
        updated = db_session.query(Media).filter(Media.id == media.id).first()
        assert updated.override_require_original == 1
        assert updated.override_notify == 0

    def test_update_media_clear_overrides(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """PUT /api/v1/media/{id} can clear overrides by setting to null."""
        media = create_media_in_db(
            db_session,
            sample_instance,
            override_require_original=1,
            override_notify=0,
        )

        response = authenticated_client.put(
            f"/api/v1/media/{media.id}",
            json={
                "override_require_original": None,
                "override_notify": None,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["override_require_original"] is None
        assert data["override_notify"] is None

    def test_update_media_not_found(self, authenticated_client) -> None:
        """PUT /api/v1/media/{id} returns 404 for non-existent media."""
        response = authenticated_client.put(
            "/api/v1/media/99999",
            json={"override_require_original": True},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Media not found"


class TestGetMediaHistory:
    """Tests for GET /api/v1/media/{id}/history endpoint."""

    def test_get_media_history(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/media/{id}/history returns history for media."""
        media = create_media_in_db(db_session, sample_instance)
        create_history_in_db(db_session, media=media, event_type="scan")
        create_history_in_db(db_session, media=media, event_type="tag_updated")
        # Create unrelated history
        create_history_in_db(db_session, instance=sample_instance, event_type="instance_created")

        response = authenticated_client.get(f"/api/v1/media/{media.id}/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        event_types = {h["event_type"] for h in data}
        assert event_types == {"scan", "tag_updated"}

    def test_get_media_history_empty(
        self, authenticated_client, db_session: Session, sample_instance: Instance
    ) -> None:
        """GET /api/v1/media/{id}/history returns empty list when no history."""
        media = create_media_in_db(db_session, sample_instance)

        response = authenticated_client.get(f"/api/v1/media/{media.id}/history")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_media_history_not_found(self, authenticated_client) -> None:
        """GET /api/v1/media/{id}/history returns 404 for non-existent media."""
        response = authenticated_client.get("/api/v1/media/99999/history")

        assert response.status_code == 404
        assert response.json()["detail"] == "Media not found"


class TestValidatorEdgeCases:
    """Tests for validator edge cases in response models."""

    def test_season_response_with_list_values(self) -> None:
        """SeasonResponse handles fields that are already lists (not JSON strings)."""
        from taggarr.api.routes.media import SeasonResponse

        # Test validator directly with list values
        response = SeasonResponse(
            id=1,
            media_id=1,
            season_number=1,
            episode_count=10,
            status="complete",
            original_dub=["en"],  # Already a list, not JSON string
            dub=["en", "de"],
            missing_dub=["fr"],
            unexpected_languages=["es"],
            last_modified=None,
        )

        assert response.original_dub == ["en"]
        assert response.dub == ["en", "de"]
        assert response.missing_dub == ["fr"]
        assert response.unexpected_languages == ["es"]

    def test_media_with_no_tag(
        self,
        authenticated_client,
        db_session: Session,
        sample_instance: Instance,
    ) -> None:
        """Media with no tag assigned returns tag_id and tag_label as None."""
        media = create_media_in_db(db_session, sample_instance, tag=None)

        response = authenticated_client.get(f"/api/v1/media/{media.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["tag_id"] is None
        assert data["tag_label"] is None

    def test_media_with_no_seasons(
        self,
        authenticated_client,
        db_session: Session,
        sample_instance: Instance,
    ) -> None:
        """Media with no seasons returns empty seasons list."""
        media = create_media_in_db(db_session, sample_instance)
        # Don't create any seasons

        response = authenticated_client.get(f"/api/v1/media/{media.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["seasons"] == []

    def test_media_list_item_with_bool_override_values(self) -> None:
        """MediaListItem handles override fields that are already bools (not ints)."""
        from taggarr.api.routes.media import MediaListItem

        # Test validator directly with boolean values
        response = MediaListItem(
            id=1,
            instance_id=1,
            title="Test Show",
            path="/media/tv/Test",
            media_type="series",
            original_language="en",
            tag_id=None,
            added=datetime.now(),
            last_scanned=None,
            override_require_original=True,  # Boolean, not int
            override_notify=False,  # Boolean, not int
        )

        assert response.override_require_original is True
        assert response.override_notify is False

    def test_history_with_null_data(
        self,
        authenticated_client,
        db_session: Session,
        sample_instance: Instance,
    ) -> None:
        """History entry with null data returns data as None."""
        media = create_media_in_db(db_session, sample_instance)
        history = History(
            date=datetime.now(),
            event_type="scan",
            media_id=media.id,
            instance_id=None,
            data=None,  # Null data
        )
        db_session.add(history)
        db_session.commit()

        response = authenticated_client.get(f"/api/v1/media/{media.id}/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["data"] is None

    def test_history_response_with_dict_data(self) -> None:
        """HistoryResponse handles data that is already a dict (not JSON string)."""
        from taggarr.api.routes.media import HistoryResponse

        # Test validator directly with dict value
        response = HistoryResponse(
            id=1,
            date=datetime.now(),
            event_type="tag_updated",
            media_id=1,
            instance_id=None,
            data={"old_tag": "dub", "new_tag": "semi-dub"},  # Already a dict
        )

        assert response.data == {"old_tag": "dub", "new_tag": "semi-dub"}


class TestMediaAuthRequired:
    """Tests for authentication requirement on media routes."""

    def test_media_routes_require_auth(self, client) -> None:
        """All media endpoints return 401 without authentication."""
        # GET /api/v1/media
        response = client.get("/api/v1/media")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/media/{id}
        response = client.get("/api/v1/media/1")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # PUT /api/v1/media/{id}
        response = client.put("/api/v1/media/1", json={"override_require_original": True})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/media/{id}/history
        response = client.get("/api/v1/media/1/history")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
