"""Tests for API key management routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from taggarr.api.app import create_app
from taggarr.auth import (
    create_session_token,
    get_session_expiry,
    hash_api_key,
    hash_password,
)
from taggarr.db import ApiKey, Base, SessionModel, User, init_db


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


class TestListApiKeys:
    """Tests for GET /api/v1/apikey endpoint."""

    def test_list_api_keys_empty(self, authenticated_client) -> None:
        """GET /api/v1/apikey returns empty list when no keys exist."""
        response = authenticated_client.get("/api/v1/apikey")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_api_keys_returns_keys(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/apikey returns list of API keys without actual key."""
        # Create some API keys
        api_key1 = ApiKey(
            label="Test Key 1",
            key=hash_api_key("test-key-1"),
        )
        api_key2 = ApiKey(
            label="Test Key 2",
            key=hash_api_key("test-key-2"),
        )
        db_session.add(api_key1)
        db_session.add(api_key2)
        db_session.commit()

        response = authenticated_client.get("/api/v1/apikey")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verify keys are NOT exposed
        for item in data:
            assert "key" not in item
            assert "id" in item
            assert "label" in item
            assert "last_used_at" in item


class TestCreateApiKey:
    """Tests for POST /api/v1/apikey endpoint."""

    def test_create_api_key_returns_key(self, authenticated_client) -> None:
        """POST /api/v1/apikey creates key and returns it once."""
        response = authenticated_client.post(
            "/api/v1/apikey",
            json={"label": "My API Key"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["label"] == "My API Key"
        assert "key" in data
        # Key should be 32 characters (URL-safe base64 of 24 bytes)
        assert len(data["key"]) == 32

    def test_create_api_key_stores_hashed(
        self, authenticated_client, db_session: Session
    ) -> None:
        """POST /api/v1/apikey stores hashed key, not plaintext."""
        response = authenticated_client.post(
            "/api/v1/apikey",
            json={"label": "Hashed Key Test"},
        )

        assert response.status_code == 201
        data = response.json()
        raw_key = data["key"]

        # Refresh session to get the stored key
        db_session.expire_all()
        stored_key = db_session.query(ApiKey).filter(ApiKey.id == data["id"]).first()

        assert stored_key is not None
        # Stored key should NOT equal raw key
        assert stored_key.key != raw_key
        # Stored key should be the hash
        assert stored_key.key == hash_api_key(raw_key)


class TestDeleteApiKey:
    """Tests for DELETE /api/v1/apikey/{id} endpoint."""

    def test_delete_api_key_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """DELETE /api/v1/apikey/{id} deletes existing key."""
        # Create an API key
        api_key = ApiKey(
            label="Key to delete",
            key=hash_api_key("delete-me"),
        )
        db_session.add(api_key)
        db_session.commit()
        key_id = api_key.id

        response = authenticated_client.delete(f"/api/v1/apikey/{key_id}")

        assert response.status_code == 204

        # Verify key was deleted
        db_session.expire_all()
        deleted_key = db_session.query(ApiKey).filter(ApiKey.id == key_id).first()
        assert deleted_key is None

    def test_delete_api_key_not_found(self, authenticated_client) -> None:
        """DELETE /api/v1/apikey/{id} returns 404 for non-existent key."""
        response = authenticated_client.delete("/api/v1/apikey/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "API key not found"


class TestApiKeyAuthRequired:
    """Tests for authentication requirement on API key routes."""

    def test_api_key_routes_require_auth(self, client) -> None:
        """All API key endpoints return 401 without authentication."""
        # GET /api/v1/apikey
        response = client.get("/api/v1/apikey")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # POST /api/v1/apikey
        response = client.post("/api/v1/apikey", json={"label": "Test"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # DELETE /api/v1/apikey/{id}
        response = client.delete("/api/v1/apikey/1")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
