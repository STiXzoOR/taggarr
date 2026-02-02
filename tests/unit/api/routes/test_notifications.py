"""Tests for notification management routes."""

import json
from unittest.mock import AsyncMock, patch

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
from taggarr.db import Base, Notification, SessionModel, User, init_db


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


def create_notification_in_db(db_session: Session, **kwargs) -> Notification:
    """Helper to create a notification in the database."""
    defaults = {
        "name": "test-notification",
        "implementation": "discord",
        "settings": json.dumps({"webhook_url": "https://discord.com/webhook"}),
        "on_scan_completed": 0,
        "on_wrong_dub_detected": 1,
        "on_original_missing": 1,
        "on_health_issue": 0,
        "on_application_update": 0,
        "include_health_warnings": 0,
        "tags": None,
    }
    defaults.update(kwargs)
    notification = Notification(**defaults)
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return notification


class TestListNotifications:
    """Tests for GET /api/v1/notification endpoint."""

    def test_list_notifications_empty(self, authenticated_client) -> None:
        """GET /api/v1/notification returns empty list when no notifications exist."""
        response = authenticated_client.get("/api/v1/notification")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_notifications_returns_all(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/notification returns all notifications."""
        create_notification_in_db(db_session, name="discord-notify")
        create_notification_in_db(
            db_session,
            name="telegram-notify",
            implementation="telegram",
            settings=json.dumps({"bot_token": "token", "chat_id": "123"}),
        )

        response = authenticated_client.get("/api/v1/notification")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {n["name"] for n in data}
        assert names == {"discord-notify", "telegram-notify"}


class TestGetNotification:
    """Tests for GET /api/v1/notification/{id} endpoint."""

    def test_get_notification_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/notification/{id} returns notification details."""
        notification = create_notification_in_db(
            db_session,
            name="my-discord",
            implementation="discord",
        )

        response = authenticated_client.get(f"/api/v1/notification/{notification.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == notification.id
        assert data["name"] == "my-discord"
        assert data["implementation"] == "discord"

    def test_get_notification_with_tags(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/notification/{id} returns notification with tags parsed from JSON."""
        notification = create_notification_in_db(
            db_session,
            name="discord-with-tags",
            implementation="discord",
            tags=json.dumps(["dub", "semi-dub"]),
        )

        response = authenticated_client.get(f"/api/v1/notification/{notification.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["tags"] == ["dub", "semi-dub"]

    def test_get_notification_not_found(self, authenticated_client) -> None:
        """GET /api/v1/notification/{id} returns 404 for non-existent notification."""
        response = authenticated_client.get("/api/v1/notification/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Notification not found"


class TestCreateNotification:
    """Tests for POST /api/v1/notification endpoint."""

    def test_create_notification_success(self, authenticated_client) -> None:
        """POST /api/v1/notification creates new notification."""
        response = authenticated_client.post(
            "/api/v1/notification",
            json={
                "name": "my-discord",
                "implementation": "discord",
                "settings": {"webhook_url": "https://discord.com/api/webhooks/123"},
                "on_wrong_dub_detected": True,
                "on_original_missing": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "my-discord"
        assert data["implementation"] == "discord"
        assert data["on_wrong_dub_detected"] is True

    def test_create_notification_duplicate_name(
        self, authenticated_client, db_session: Session
    ) -> None:
        """POST /api/v1/notification returns 400 for duplicate name."""
        create_notification_in_db(db_session, name="my-discord")

        response = authenticated_client.post(
            "/api/v1/notification",
            json={
                "name": "my-discord",
                "implementation": "discord",
                "settings": {"webhook_url": "https://discord.com/api/webhooks/456"},
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestUpdateNotification:
    """Tests for PUT /api/v1/notification/{id} endpoint."""

    def test_update_notification_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/notification/{id} updates notification."""
        notification = create_notification_in_db(
            db_session,
            name="old-name",
            on_wrong_dub_detected=0,
        )

        response = authenticated_client.put(
            f"/api/v1/notification/{notification.id}",
            json={"name": "new-name", "on_wrong_dub_detected": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new-name"
        assert data["on_wrong_dub_detected"] is True

    def test_update_notification_duplicate_name(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/notification/{id} returns 400 for duplicate name."""
        create_notification_in_db(db_session, name="existing-notification")
        notification = create_notification_in_db(db_session, name="my-notification")

        response = authenticated_client.put(
            f"/api/v1/notification/{notification.id}",
            json={"name": "existing-notification"},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_update_notification_settings(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/notification/{id} updates settings."""
        notification = create_notification_in_db(db_session, name="test-update-settings")

        response = authenticated_client.put(
            f"/api/v1/notification/{notification.id}",
            json={"settings": {"webhook_url": "https://new-webhook.com"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["settings"]["webhook_url"] == "https://new-webhook.com"

    def test_update_notification_tags(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/notification/{id} updates tags."""
        notification = create_notification_in_db(db_session, name="test-update-tags")

        response = authenticated_client.put(
            f"/api/v1/notification/{notification.id}",
            json={"tags": ["dub", "semi-dub"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tags"] == ["dub", "semi-dub"]

    def test_update_notification_tags_to_null(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/notification/{id} can set tags to null."""
        notification = create_notification_in_db(
            db_session,
            name="test-tags-null",
            tags=json.dumps(["dub"]),
        )

        response = authenticated_client.put(
            f"/api/v1/notification/{notification.id}",
            json={"tags": None},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tags"] is None

    def test_update_notification_not_found(self, authenticated_client) -> None:
        """PUT /api/v1/notification/{id} returns 404 for non-existent notification."""
        response = authenticated_client.put(
            "/api/v1/notification/99999",
            json={"name": "updated"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Notification not found"

    def test_update_notification_with_null_value_skipped(
        self, authenticated_client, db_session: Session
    ) -> None:
        """PUT /api/v1/notification/{id} skips None values for non-nullable fields."""
        notification = create_notification_in_db(
            db_session,
            name="test-skip-null",
            implementation="discord",
        )

        # Send explicit null for implementation (which should be skipped)
        response = authenticated_client.put(
            f"/api/v1/notification/{notification.id}",
            json={"implementation": None},
        )

        assert response.status_code == 200
        data = response.json()
        # Implementation should remain unchanged since None is skipped
        assert data["implementation"] == "discord"


class TestDeleteNotification:
    """Tests for DELETE /api/v1/notification/{id} endpoint."""

    def test_delete_notification_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """DELETE /api/v1/notification/{id} deletes notification."""
        notification = create_notification_in_db(db_session, name="to-delete")
        notification_id = notification.id

        response = authenticated_client.delete(f"/api/v1/notification/{notification_id}")

        assert response.status_code == 204

        # Verify notification was deleted
        db_session.expire_all()
        deleted = (
            db_session.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )
        assert deleted is None

    def test_delete_notification_not_found(self, authenticated_client) -> None:
        """DELETE /api/v1/notification/{id} returns 404 for non-existent notification."""
        response = authenticated_client.delete("/api/v1/notification/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Notification not found"


class TestNotificationSchema:
    """Tests for GET /api/v1/notification/schema endpoint."""

    def test_notification_schema_returns_providers(self, authenticated_client) -> None:
        """GET /api/v1/notification/schema returns list of available providers."""
        response = authenticated_client.get("/api/v1/notification/schema")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify Discord provider is present
        discord = next((p for p in data if p["id"] == "discord"), None)
        assert discord is not None
        assert discord["name"] == "Discord"
        assert "webhook_url" in discord["config_fields"]

        # Verify Telegram provider is present
        telegram = next((p for p in data if p["id"] == "telegram"), None)
        assert telegram is not None
        assert "bot_token" in telegram["config_fields"]
        assert "chat_id" in telegram["config_fields"]


class TestTestNotification:
    """Tests for POST /api/v1/notification/test endpoint."""

    @patch("taggarr.api.routes.notifications.get_provider")
    def test_test_notification_success(
        self, mock_get_provider, authenticated_client
    ) -> None:
        """POST /api/v1/notification/test returns success for valid config."""
        # Mock the provider to return success
        mock_provider = AsyncMock()
        mock_provider.test.return_value = (True, "Test successful")
        mock_get_provider.return_value = lambda: mock_provider

        response = authenticated_client.post(
            "/api/v1/notification/test",
            json={
                "implementation": "discord",
                "settings": {"webhook_url": "https://discord.com/api/webhooks/123"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data

    def test_test_notification_unknown_implementation(
        self, authenticated_client
    ) -> None:
        """POST /api/v1/notification/test returns failure for unknown implementation."""
        response = authenticated_client.post(
            "/api/v1/notification/test",
            json={
                "implementation": "unknown_provider",
                "settings": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Unknown implementation" in data["message"]


class TestNotificationAuthRequired:
    """Tests for authentication requirement on notification routes."""

    def test_notification_routes_require_auth(self, client) -> None:
        """All notification endpoints return 401 without authentication."""
        # GET /api/v1/notification
        response = client.get("/api/v1/notification")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/notification/{id}
        response = client.get("/api/v1/notification/1")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # POST /api/v1/notification
        response = client.post("/api/v1/notification", json={"name": "test"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # PUT /api/v1/notification/{id}
        response = client.put("/api/v1/notification/1", json={"name": "test"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # DELETE /api/v1/notification/{id}
        response = client.delete("/api/v1/notification/1")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # POST /api/v1/notification/test
        response = client.post(
            "/api/v1/notification/test",
            json={"implementation": "discord", "settings": {}},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/notification/schema
        response = client.get("/api/v1/notification/schema")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
