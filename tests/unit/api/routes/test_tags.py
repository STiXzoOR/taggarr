"""Tests for tag routes."""

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
from taggarr.db import Base, Instance, Media, SessionModel, Tag, User, init_db


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


def create_tag_in_db(db_session: Session, label: str) -> Tag:
    """Helper to create a tag in the database."""
    existing = db_session.query(Tag).filter(Tag.label == label).first()
    if existing:
        return existing
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


class TestListTags:
    """Tests for GET /api/v1/tag endpoint."""

    def test_list_tags_returns_all(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/tag returns all tags with counts."""
        # Create tags
        create_tag_in_db(db_session, "dub")
        create_tag_in_db(db_session, "semi-dub")
        create_tag_in_db(db_session, "wrong-dub")

        response = authenticated_client.get("/api/v1/tag")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        labels = {t["label"] for t in data}
        assert labels == {"dub", "semi-dub", "wrong-dub"}

    def test_list_tags_with_media_counts(
        self,
        authenticated_client,
        db_session: Session,
        sample_instance: Instance,
    ) -> None:
        """GET /api/v1/tag returns accurate media counts."""
        # Create tags
        dub_tag = create_tag_in_db(db_session, "dub")
        semi_dub_tag = create_tag_in_db(db_session, "semi-dub")
        wrong_dub_tag = create_tag_in_db(db_session, "wrong-dub")

        # Create media with different tags
        create_media_in_db(db_session, sample_instance, tag=dub_tag, title="Show 1", path="/media/tv/Show1", clean_title="show1")
        create_media_in_db(db_session, sample_instance, tag=dub_tag, title="Show 2", path="/media/tv/Show2", clean_title="show2")
        create_media_in_db(db_session, sample_instance, tag=dub_tag, title="Show 3", path="/media/tv/Show3", clean_title="show3")
        create_media_in_db(db_session, sample_instance, tag=semi_dub_tag, title="Show 4", path="/media/tv/Show4", clean_title="show4")
        # wrong-dub has no media

        response = authenticated_client.get("/api/v1/tag")

        assert response.status_code == 200
        data = response.json()

        # Find each tag and verify count
        tag_counts = {t["label"]: t["media_count"] for t in data}
        assert tag_counts["dub"] == 3
        assert tag_counts["semi-dub"] == 1
        assert tag_counts["wrong-dub"] == 0

    def test_list_tags_returns_default_tags(self, authenticated_client) -> None:
        """GET /api/v1/tag returns default seeded tags when no media exists."""
        response = authenticated_client.get("/api/v1/tag")

        assert response.status_code == 200
        data = response.json()
        # Database is seeded with default tags: dub, semi-dub, wrong-dub
        assert len(data) == 3
        labels = {t["label"] for t in data}
        assert labels == {"dub", "semi-dub", "wrong-dub"}
        # All should have zero media count
        for tag in data:
            assert tag["media_count"] == 0


class TestGetTag:
    """Tests for GET /api/v1/tag/{id} endpoint."""

    def test_get_tag_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/tag/{id} returns tag by ID."""
        tag = create_tag_in_db(db_session, "dub")

        response = authenticated_client.get(f"/api/v1/tag/{tag.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tag.id
        assert data["label"] == "dub"

    def test_get_tag_not_found(self, authenticated_client) -> None:
        """GET /api/v1/tag/{id} returns 404 for non-existent tag."""
        response = authenticated_client.get("/api/v1/tag/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Tag not found"


class TestTagAuthRequired:
    """Tests for authentication requirement on tag routes."""

    def test_tag_routes_require_auth(self, client) -> None:
        """All tag endpoints return 401 without authentication."""
        # GET /api/v1/tag
        response = client.get("/api/v1/tag")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/tag/{id}
        response = client.get("/api/v1/tag/1")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
