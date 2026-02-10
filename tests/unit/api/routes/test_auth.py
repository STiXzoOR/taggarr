"""Tests for authentication API routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from taggarr.api.app import create_app
from taggarr.db import Base, SessionModel, User, init_db
from taggarr.auth import hash_password, create_session_token, get_session_expiry


@pytest.fixture
def engine():
    """Create an in-memory SQLite database engine with thread safety."""
    # Use StaticPool for in-memory SQLite to allow multi-threaded access
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


class TestInitialize:
    """Tests for POST /api/v1/initialize endpoint."""

    def test_initialize_creates_admin_user(self, client, db_session: Session) -> None:
        """POST /api/v1/initialize creates first admin user."""
        response = client.post(
            "/api/v1/initialize",
            json={"username": "admin", "password": "adminpassword"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "System initialized successfully"}

        # Verify user was created
        user = db_session.query(User).filter(User.username == "admin").first()
        assert user is not None
        assert user.username == "admin"

        # Verify session cookie was set
        assert "session" in response.cookies

    def test_initialize_fails_if_already_initialized(
        self, client, test_user
    ) -> None:
        """POST /api/v1/initialize fails if user already exists."""
        response = client.post(
            "/api/v1/initialize",
            json={"username": "admin2", "password": "password2"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "System already initialized"


class TestLogin:
    """Tests for POST /api/v1/auth/login endpoint."""

    def test_login_success(self, client, test_user) -> None:
        """POST /api/v1/auth/login succeeds with valid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "Login successful"}
        assert "session" in response.cookies

    def test_login_invalid_credentials(self, client, test_user) -> None:
        """POST /api/v1/auth/login fails with invalid password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid username or password"

    def test_login_invalid_username(self, client, test_user) -> None:
        """POST /api/v1/auth/login fails with non-existent username."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "testpassword"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid username or password"


class TestLogout:
    """Tests for POST /api/v1/auth/logout endpoint."""

    def test_logout_clears_session(self, authenticated_client, db_session) -> None:
        """POST /api/v1/auth/logout clears session and cookie."""
        response = authenticated_client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        assert response.json() == {"message": "Logout successful"}

        # Verify session cookie was deleted (set to empty or expired)
        # TestClient handles this differently, so we check the response
        assert response.headers.get("set-cookie") is not None

    def test_logout_requires_authentication(self, client) -> None:
        """POST /api/v1/auth/logout requires valid session."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"


class TestAuthStatus:
    """Tests for GET /api/v1/auth/status endpoint."""

    def test_auth_status_unauthenticated(self, client) -> None:
        """GET /api/v1/auth/status returns unauthenticated status."""
        response = client.get("/api/v1/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["user"] is None
        assert data["initialized"] is False

    def test_auth_status_authenticated(self, authenticated_client, test_user) -> None:
        """GET /api/v1/auth/status returns user info when authenticated."""
        response = authenticated_client.get("/api/v1/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"]["username"] == "testuser"
        assert data["initialized"] is True

    def test_auth_status_shows_initialized_when_user_exists(
        self, client, test_user
    ) -> None:
        """GET /api/v1/auth/status shows initialized=True when users exist."""
        response = client.get("/api/v1/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["initialized"] is True


class TestExpiredSession:
    """Tests for expired session handling."""

    def test_expired_session_returns_unauthorized(
        self, client, db_session: Session, test_user
    ) -> None:
        """Expired session returns 401 on protected routes."""
        from datetime import datetime, timedelta, timezone

        # Create expired session
        token = create_session_token()
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)

        session = SessionModel(
            identifier=token,
            user_id=test_user.id,
            expires_at=expired_time,
        )
        db_session.add(session)
        db_session.commit()

        client.cookies.set("session", token)

        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401
        assert response.json()["detail"] == "Session expired or invalid"
