"""Tests for command routes."""

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
from taggarr.db import Base, Command, SessionModel, User, init_db


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


def create_command_in_db(
    db_session: Session,
    name: str = "ScanInstance",
    body: str | None = None,
    status: str = "Queued",
    queued_at: datetime | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    trigger: str = "manual",
) -> Command:
    """Helper to create a command in the database."""
    command = Command(
        name=name,
        body=body,
        status=status,
        queued_at=queued_at or datetime.now(),
        started_at=started_at,
        ended_at=ended_at,
        trigger=trigger,
    )
    db_session.add(command)
    db_session.commit()
    db_session.refresh(command)
    return command


class TestListCommands:
    """Tests for GET /api/v1/command endpoint."""

    def test_list_commands_empty(self, authenticated_client) -> None:
        """GET /api/v1/command returns empty list when no commands exist."""
        response = authenticated_client.get("/api/v1/command")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_commands_returns_recent(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/command returns commands ordered by queued_at descending."""
        # Create commands at different times
        cmd1 = create_command_in_db(
            db_session,
            name="ScanInstance",
            queued_at=datetime(2024, 1, 1, 10, 0, 0),
        )
        cmd2 = create_command_in_db(
            db_session,
            name="ScanMedia",
            queued_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        cmd3 = create_command_in_db(
            db_session,
            name="RefreshTags",
            queued_at=datetime(2024, 1, 1, 11, 0, 0),
        )

        response = authenticated_client.get("/api/v1/command")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Should be ordered by queued_at descending (newest first)
        assert data[0]["id"] == cmd2.id
        assert data[0]["name"] == "ScanMedia"
        assert data[1]["id"] == cmd3.id
        assert data[1]["name"] == "RefreshTags"
        assert data[2]["id"] == cmd1.id
        assert data[2]["name"] == "ScanInstance"


class TestGetCommand:
    """Tests for GET /api/v1/command/{id} endpoint."""

    def test_get_command_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/command/{id} returns command by ID."""
        command = create_command_in_db(
            db_session,
            name="ScanInstance",
            body='{"instance_id": 1}',
            status="Completed",
        )

        response = authenticated_client.get(f"/api/v1/command/{command.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == command.id
        assert data["name"] == "ScanInstance"
        assert data["body"] == '{"instance_id": 1}'
        assert data["status"] == "Completed"

    def test_get_command_not_found(self, authenticated_client) -> None:
        """GET /api/v1/command/{id} returns 404 for non-existent command."""
        response = authenticated_client.get("/api/v1/command/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Command not found"


class TestCreateCommand:
    """Tests for POST /api/v1/command endpoint."""

    def test_create_command_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """POST /api/v1/command creates a queued command."""
        response = authenticated_client.post(
            "/api/v1/command",
            json={"name": "ScanInstance", "body": {"instance_id": 1}},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "ScanInstance"
        assert data["status"] == "Queued"
        assert data["body"] == '{"instance_id": 1}'
        assert "id" in data
        assert "queued_at" in data

        # Verify persisted in database
        command = db_session.query(Command).filter(Command.id == data["id"]).first()
        assert command is not None
        assert command.name == "ScanInstance"
        assert command.status == "Queued"

    def test_create_command_without_body(
        self, authenticated_client, db_session: Session
    ) -> None:
        """POST /api/v1/command creates command without body."""
        response = authenticated_client.post(
            "/api/v1/command",
            json={"name": "RefreshTags"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "RefreshTags"
        assert data["body"] is None


class TestCancelCommand:
    """Tests for DELETE /api/v1/command/{id} endpoint."""

    def test_cancel_command_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """DELETE /api/v1/command/{id} cancels a queued command."""
        command = create_command_in_db(db_session, status="Queued")
        command_id = command.id  # Store ID before it might be deleted

        response = authenticated_client.delete(f"/api/v1/command/{command_id}")

        assert response.status_code == 200
        assert response.json()["message"] == "Command cancelled"

        # Verify deleted from database
        db_session.expire_all()
        deleted_command = (
            db_session.query(Command).filter(Command.id == command_id).first()
        )
        assert deleted_command is None

    def test_cancel_command_already_started(
        self, authenticated_client, db_session: Session
    ) -> None:
        """DELETE /api/v1/command/{id} returns 400 for started command."""
        command = create_command_in_db(
            db_session,
            status="Started",
            started_at=datetime.now(),
        )

        response = authenticated_client.delete(f"/api/v1/command/{command.id}")

        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot cancel command that is not queued"

    def test_cancel_command_already_completed(
        self, authenticated_client, db_session: Session
    ) -> None:
        """DELETE /api/v1/command/{id} returns 400 for completed command."""
        command = create_command_in_db(
            db_session,
            status="Completed",
            started_at=datetime.now(),
            ended_at=datetime.now(),
        )

        response = authenticated_client.delete(f"/api/v1/command/{command.id}")

        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot cancel command that is not queued"

    def test_cancel_command_not_found(self, authenticated_client) -> None:
        """DELETE /api/v1/command/{id} returns 404 for non-existent command."""
        response = authenticated_client.delete("/api/v1/command/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Command not found"


class TestCommandAuthRequired:
    """Tests for authentication requirement on command routes."""

    def test_command_routes_require_auth(self, client) -> None:
        """All command endpoints return 401 without authentication."""
        # GET /api/v1/command
        response = client.get("/api/v1/command")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/command/{id}
        response = client.get("/api/v1/command/1")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # POST /api/v1/command
        response = client.post("/api/v1/command", json={"name": "ScanInstance"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # DELETE /api/v1/command/{id}
        response = client.delete("/api/v1/command/1")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
