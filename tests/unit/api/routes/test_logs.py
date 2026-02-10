"""Tests for log routes."""

from datetime import datetime, timezone

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
    Base,
    SessionModel,
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


class TestGetLogs:
    """Tests for GET /api/v1/log endpoint."""

    def test_get_logs_returns_empty(self, authenticated_client) -> None:
        """GET /api/v1/log returns empty list (stub implementation)."""
        response = authenticated_client.get("/api/v1/log")

        assert response.status_code == 200
        data = response.json()

        assert "entries" in data
        assert "total" in data
        assert data["entries"] == []
        assert data["total"] == 0


class TestListLogFiles:
    """Tests for GET /api/v1/log/file endpoint."""

    def test_list_log_files_returns_empty(self, authenticated_client) -> None:
        """GET /api/v1/log/file returns empty list (stub implementation)."""
        response = authenticated_client.get("/api/v1/log/file")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert data == []


class TestDownloadLogFile:
    """Tests for GET /api/v1/log/file/{name} endpoint."""

    def test_download_log_file_not_implemented(self, authenticated_client) -> None:
        """GET /api/v1/log/file/{name} returns 501 Not Implemented."""
        response = authenticated_client.get("/api/v1/log/file/test.log")

        assert response.status_code == 501
        data = response.json()
        assert "detail" in data
        assert "not implemented" in data["detail"].lower()


class TestLogRoutesRequireAuth:
    """Tests for authentication requirement on log routes."""

    def test_log_routes_require_auth(self, client) -> None:
        """All log endpoints return 401 without authentication."""
        # GET /api/v1/log
        response = client.get("/api/v1/log")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/log/file
        response = client.get("/api/v1/log/file")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/log/file/{name}
        response = client.get("/api/v1/log/file/test.log")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
