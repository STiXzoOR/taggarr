"""Tests for backup routes."""

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
from taggarr.db import Backup, Base, SessionModel, User, init_db


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


def create_backup_in_db(
    db_session: Session,
    **kwargs,
) -> Backup:
    """Helper to create a backup in the database."""
    defaults = {
        "filename": "taggarr_backup_20240115_120000.zip",
        "path": "/backups/taggarr_backup_20240115_120000.zip",
        "type": "manual",
        "size_bytes": 1024,
        "created_at": datetime.now(),
    }
    defaults.update(kwargs)
    backup = Backup(**defaults)
    db_session.add(backup)
    db_session.commit()
    db_session.refresh(backup)
    return backup


class TestListBackups:
    """Tests for GET /api/v1/backup endpoint."""

    def test_list_backups_empty(self, authenticated_client) -> None:
        """GET /api/v1/backup returns empty list when no backups exist."""
        response = authenticated_client.get("/api/v1/backup")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_backups_returns_all(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/backup returns all backups."""
        # Create multiple backups
        backup1 = create_backup_in_db(
            db_session,
            filename="backup1.zip",
            path="/backups/backup1.zip",
            type="manual",
            size_bytes=1024,
        )
        backup2 = create_backup_in_db(
            db_session,
            filename="backup2.zip",
            path="/backups/backup2.zip",
            type="scheduled",
            size_bytes=2048,
        )

        response = authenticated_client.get("/api/v1/backup")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Check structure of returned backups
        filenames = {b["filename"] for b in data}
        assert filenames == {"backup1.zip", "backup2.zip"}

        # Check required fields are present
        for backup in data:
            assert "id" in backup
            assert "filename" in backup
            assert "size" in backup
            assert "type" in backup
            assert "created_at" in backup


class TestCreateBackup:
    """Tests for POST /api/v1/backup endpoint."""

    def test_create_backup_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """POST /api/v1/backup creates a backup record."""
        response = authenticated_client.post("/api/v1/backup")

        assert response.status_code == 201
        data = response.json()

        # Check response structure
        assert "id" in data
        assert "filename" in data
        assert "size" in data
        assert "type" in data
        assert data["type"] == "manual"
        assert "created_at" in data

        # Verify backup was created in database
        backup = db_session.query(Backup).filter(Backup.id == data["id"]).first()
        assert backup is not None
        assert backup.type == "manual"


class TestDeleteBackup:
    """Tests for DELETE /api/v1/backup/{id} endpoint."""

    def test_delete_backup_success(
        self, authenticated_client, db_session: Session
    ) -> None:
        """DELETE /api/v1/backup/{id} deletes the backup."""
        backup = create_backup_in_db(db_session)

        response = authenticated_client.delete(f"/api/v1/backup/{backup.id}")

        assert response.status_code == 204

        # Verify backup was deleted
        deleted = db_session.query(Backup).filter(Backup.id == backup.id).first()
        assert deleted is None

    def test_delete_backup_not_found(self, authenticated_client) -> None:
        """DELETE /api/v1/backup/{id} returns 404 for non-existent backup."""
        response = authenticated_client.delete("/api/v1/backup/9999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Backup not found"


class TestDownloadBackup:
    """Tests for GET /api/v1/backup/{id}/download endpoint."""

    def test_download_backup_not_implemented(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/backup/{id}/download returns 501 Not Implemented."""
        backup = create_backup_in_db(db_session)

        response = authenticated_client.get(f"/api/v1/backup/{backup.id}/download")

        assert response.status_code == 501
        assert response.json()["detail"] == "Backup download not yet implemented"


class TestRestoreBackup:
    """Tests for POST /api/v1/backup/{id}/restore endpoint."""

    def test_restore_backup_not_implemented(
        self, authenticated_client, db_session: Session
    ) -> None:
        """POST /api/v1/backup/{id}/restore returns 501 Not Implemented."""
        backup = create_backup_in_db(db_session)

        response = authenticated_client.post(f"/api/v1/backup/{backup.id}/restore")

        assert response.status_code == 501
        assert response.json()["detail"] == "Backup restore not yet implemented"


class TestBackupAuthRequired:
    """Tests for authentication requirement on backup routes."""

    def test_backup_routes_require_auth(self, client, db_session: Session) -> None:
        """All backup endpoints return 401 without authentication."""
        # Create a backup for routes that need an ID
        backup = create_backup_in_db(db_session)

        # GET /api/v1/backup
        response = client.get("/api/v1/backup")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # POST /api/v1/backup
        response = client.post("/api/v1/backup")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # DELETE /api/v1/backup/{id}
        response = client.delete(f"/api/v1/backup/{backup.id}")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # GET /api/v1/backup/{id}/download
        response = client.get(f"/api/v1/backup/{backup.id}/download")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

        # POST /api/v1/backup/{id}/restore
        response = client.post(f"/api/v1/backup/{backup.id}/restore")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
