"""Tests for configuration routes."""

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from taggarr.api.app import create_app
from taggarr.auth import create_session_token, get_session_expiry, hash_password
from taggarr.db import Base, Config, SessionModel, User, init_db


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


class TestGetConfig:
    """Tests for GET /api/v1/config/{key} endpoint."""

    def test_get_config_returns_value(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/config/{key} returns config value."""
        # Create a config entry
        config = Config(key="test.setting", value="test_value")
        db_session.add(config)
        db_session.commit()

        response = authenticated_client.get("/api/v1/config/test.setting")

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test.setting"
        assert data["value"] == "test_value"

    def test_get_config_not_found(self, authenticated_client) -> None:
        """GET /api/v1/config/{key} returns 404 for missing key."""
        response = authenticated_client.get("/api/v1/config/nonexistent.key")

        assert response.status_code == 404
        assert response.json()["detail"] == "Config key 'nonexistent.key' not found"


class TestSetConfig:
    """Tests for PUT /api/v1/config/{key} endpoint."""

    def test_set_config_creates_new(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/config/{key} creates new config entry."""
        response = authenticated_client.put(
            "/api/v1/config/new.setting",
            json={"value": "new_value"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "new.setting"
        assert data["value"] == "new_value"

        # Verify it was stored in database
        db_session.expire_all()
        config = db_session.query(Config).filter(Config.key == "new.setting").first()
        assert config is not None
        assert config.value == "new_value"

    def test_set_config_updates_existing(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/config/{key} updates existing config."""
        # Create existing config
        config = Config(key="existing.setting", value="old_value")
        db_session.add(config)
        db_session.commit()

        response = authenticated_client.put(
            "/api/v1/config/existing.setting",
            json={"value": "updated_value"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "existing.setting"
        assert data["value"] == "updated_value"

        # Verify it was updated in database
        db_session.expire_all()
        updated_config = (
            db_session.query(Config).filter(Config.key == "existing.setting").first()
        )
        assert updated_config is not None
        assert updated_config.value == "updated_value"


class TestGetUIConfig:
    """Tests for GET /api/v1/config/ui endpoint."""

    def test_get_ui_config_defaults(self, authenticated_client) -> None:
        """GET /api/v1/config/ui returns default UI config."""
        response = authenticated_client.get("/api/v1/config/ui")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"
        assert data["language"] == "en"
        assert data["page_size"] == 25
        assert data["auto_refresh"] is True

    def test_get_ui_config_custom(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/config/ui returns custom UI config values."""
        # Set custom UI config values
        configs = [
            Config(key="ui.theme", value="light"),
            Config(key="ui.language", value="de"),
            Config(key="ui.page_size", value="50"),
            Config(key="ui.auto_refresh", value="false"),
        ]
        for c in configs:
            db_session.add(c)
        db_session.commit()

        response = authenticated_client.get("/api/v1/config/ui")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"
        assert data["language"] == "de"
        assert data["page_size"] == 50
        assert data["auto_refresh"] is False


class TestConfigAuthRequired:
    """Tests for authentication requirement on config routes."""

    def test_config_routes_require_auth(self, client) -> None:
        """All config endpoints return 401 without authentication."""
        # GET /api/v1/config/{key}
        response = client.get("/api/v1/config/test.key")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # PUT /api/v1/config/{key}
        response = client.put("/api/v1/config/test.key", json={"value": "test"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/config/ui
        response = client.get("/api/v1/config/ui")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
