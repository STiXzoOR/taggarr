"""Tests for instance management routes."""

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
from taggarr.db import Base, Instance, SessionModel, User, init_db


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
    from datetime import datetime

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
def sample_instance_data():
    """Sample instance data for creating new instances."""
    return {
        "name": "sonarr-main",
        "type": "sonarr",
        "url": "http://sonarr:8989",
        "api_key": "test-api-key-123",
        "root_path": "/media/tv",
        "target_languages": ["en", "de"],
        "tags": ["dub", "semi-dub", "wrong-dub"],
        "target_genre": None,
        "quick_mode": False,
        "enabled": True,
        "require_original_default": True,
        "notify_on_wrong_dub": True,
        "notify_on_original_missing": False,
    }


def create_instance_in_db(db_session: Session, **kwargs) -> Instance:
    """Helper to create an instance in the database."""
    import json

    defaults = {
        "name": "test-instance",
        "type": "sonarr",
        "url": "http://localhost:8989",
        "api_key": "test-key",
        "root_path": "/media/tv",
        "target_languages": json.dumps(["en"]),
        "tags": json.dumps(["dub"]),
        "target_genre": None,
        "quick_mode": 0,
        "enabled": 1,
        "require_original_default": 1,
        "notify_on_wrong_dub": 1,
        "notify_on_original_missing": 0,
    }
    defaults.update(kwargs)
    instance = Instance(**defaults)
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


class TestListInstances:
    """Tests for GET /api/v1/instance endpoint."""

    def test_list_instances_empty(self, authenticated_client) -> None:
        """GET /api/v1/instance returns empty list when no instances exist."""
        response = authenticated_client.get("/api/v1/instance")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_instances_returns_all(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/instance returns all instances."""
        create_instance_in_db(db_session, name="sonarr-1", type="sonarr")
        create_instance_in_db(db_session, name="radarr-1", type="radarr")

        response = authenticated_client.get("/api/v1/instance")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {inst["name"] for inst in data}
        assert names == {"sonarr-1", "radarr-1"}


class TestGetInstance:
    """Tests for GET /api/v1/instance/{id} endpoint."""

    def test_get_instance_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/instance/{id} returns instance details."""
        instance = create_instance_in_db(
            db_session,
            name="my-sonarr",
            type="sonarr",
            url="http://sonarr:8989",
        )

        response = authenticated_client.get(f"/api/v1/instance/{instance.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == instance.id
        assert data["name"] == "my-sonarr"
        assert data["type"] == "sonarr"
        assert data["url"] == "http://sonarr:8989"

    def test_get_instance_not_found(self, authenticated_client) -> None:
        """GET /api/v1/instance/{id} returns 404 for non-existent instance."""
        response = authenticated_client.get("/api/v1/instance/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Instance not found"


class TestCreateInstance:
    """Tests for POST /api/v1/instance endpoint."""

    def test_create_instance_success(
        self, authenticated_client, sample_instance_data
    ) -> None:
        """POST /api/v1/instance creates new instance."""
        response = authenticated_client.post(
            "/api/v1/instance",
            json=sample_instance_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "sonarr-main"
        assert data["type"] == "sonarr"
        assert data["url"] == "http://sonarr:8989"
        assert data["target_languages"] == ["en", "de"]

    def test_create_instance_duplicate_name(
        self, authenticated_client, db_session: Session, sample_instance_data
    ) -> None:
        """POST /api/v1/instance returns 400 for duplicate name."""
        create_instance_in_db(db_session, name="sonarr-main")

        response = authenticated_client.post(
            "/api/v1/instance",
            json=sample_instance_data,
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestUpdateInstance:
    """Tests for PUT /api/v1/instance/{id} endpoint."""

    def test_update_instance_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/instance/{id} updates instance."""
        instance = create_instance_in_db(
            db_session,
            name="old-name",
            url="http://old-url:8989",
        )

        response = authenticated_client.put(
            f"/api/v1/instance/{instance.id}",
            json={"name": "new-name", "url": "http://new-url:8989"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new-name"
        assert data["url"] == "http://new-url:8989"

    def test_update_instance_target_languages_and_tags(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/instance/{id} updates target_languages and tags."""
        instance = create_instance_in_db(db_session, name="test-update-lists")

        response = authenticated_client.put(
            f"/api/v1/instance/{instance.id}",
            json={
                "target_languages": ["en", "de", "fr"],
                "tags": ["dub", "semi-dub"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_languages"] == ["en", "de", "fr"]
        assert data["tags"] == ["dub", "semi-dub"]

    def test_update_instance_boolean_fields(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/instance/{id} updates boolean fields."""
        instance = create_instance_in_db(
            db_session,
            name="test-update-bools",
            quick_mode=0,
            enabled=1,
        )

        response = authenticated_client.put(
            f"/api/v1/instance/{instance.id}",
            json={
                "quick_mode": True,
                "enabled": False,
                "require_original_default": False,
                "notify_on_wrong_dub": False,
                "notify_on_original_missing": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quick_mode"] is True
        assert data["enabled"] is False
        assert data["require_original_default"] is False
        assert data["notify_on_wrong_dub"] is False
        assert data["notify_on_original_missing"] is True

    def test_update_instance_duplicate_name(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/instance/{id} returns 400 for duplicate name."""
        create_instance_in_db(db_session, name="existing-instance")
        instance = create_instance_in_db(db_session, name="my-instance")

        response = authenticated_client.put(
            f"/api/v1/instance/{instance.id}",
            json={"name": "existing-instance"},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_update_instance_target_genre_to_null(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/instance/{id} can set target_genre to null."""
        instance = create_instance_in_db(
            db_session,
            name="test-genre",
            target_genre="anime",
        )

        response = authenticated_client.put(
            f"/api/v1/instance/{instance.id}",
            json={"target_genre": None},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_genre"] is None

    def test_update_instance_not_found(self, authenticated_client) -> None:
        """PUT /api/v1/instance/{id} returns 404 for non-existent instance."""
        response = authenticated_client.put(
            "/api/v1/instance/99999",
            json={"name": "updated"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Instance not found"


class TestDeleteInstance:
    """Tests for DELETE /api/v1/instance/{id} endpoint."""

    def test_delete_instance_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """DELETE /api/v1/instance/{id} deletes instance."""
        instance = create_instance_in_db(db_session, name="to-delete")
        instance_id = instance.id

        response = authenticated_client.delete(f"/api/v1/instance/{instance_id}")

        assert response.status_code == 204

        # Verify instance was deleted
        db_session.expire_all()
        deleted = db_session.query(Instance).filter(Instance.id == instance_id).first()
        assert deleted is None

    def test_delete_instance_not_found(self, authenticated_client) -> None:
        """DELETE /api/v1/instance/{id} returns 404 for non-existent instance."""
        response = authenticated_client.delete("/api/v1/instance/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Instance not found"


class TestTestConnection:
    """Tests for POST /api/v1/instance/test endpoint."""

    def test_connection_success(self, authenticated_client) -> None:
        """POST /api/v1/instance/test returns success for valid URL."""
        response = authenticated_client.post(
            "/api/v1/instance/test",
            json={
                "type": "sonarr",
                "url": "http://sonarr:8989",
                "api_key": "test-key",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data

    def test_connection_invalid_url(self, authenticated_client) -> None:
        """POST /api/v1/instance/test returns failure for invalid URL."""
        response = authenticated_client.post(
            "/api/v1/instance/test",
            json={
                "type": "sonarr",
                "url": "not-a-valid-url",
                "api_key": "test-key",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Invalid URL" in data["message"]


class TestInstanceAuthRequired:
    """Tests for authentication requirement on instance routes."""

    def test_instance_routes_require_auth(self, client) -> None:
        """All instance endpoints return 401 without authentication."""
        # GET /api/v1/instance
        response = client.get("/api/v1/instance")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/instance/{id}
        response = client.get("/api/v1/instance/1")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # POST /api/v1/instance
        response = client.post("/api/v1/instance", json={"name": "test"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # PUT /api/v1/instance/{id}
        response = client.put("/api/v1/instance/1", json={"name": "test"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # DELETE /api/v1/instance/{id}
        response = client.delete("/api/v1/instance/1")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # POST /api/v1/instance/test
        response = client.post(
            "/api/v1/instance/test",
            json={"type": "sonarr", "url": "http://test", "api_key": "key"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
