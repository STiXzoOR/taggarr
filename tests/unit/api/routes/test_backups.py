"""Tests for backup routes."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    @patch("taggarr.api.routes.backups.create_backup")
    def test_create_backup_success(
        self, mock_create_backup, authenticated_client, db_session: Session, tmp_path
    ) -> None:
        """POST /api/v1/backup creates a backup record."""
        # Mock the create_backup function
        mock_backup_path = str(tmp_path / "backup.zip")
        mock_create_backup.return_value = (mock_backup_path, 1024)

        # Set up app state with db_path
        authenticated_client.app.state.db_path = tmp_path / "taggarr.db"

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


class TestCreateBackupErrors:
    """Tests for error handling in POST /api/v1/backup."""

    @patch("taggarr.api.routes.backups.create_backup")
    def test_create_backup_file_not_found(
        self, mock_create_backup, authenticated_client, tmp_path
    ) -> None:
        """POST /api/v1/backup returns 500 when database file is missing."""
        mock_create_backup.side_effect = FileNotFoundError("taggarr.db not found")
        authenticated_client.app.state.db_path = tmp_path / "taggarr.db"

        response = authenticated_client.post("/api/v1/backup")

        assert response.status_code == 500
        assert "not found" in response.json()["detail"]

    @patch("taggarr.api.routes.backups.create_backup")
    def test_create_backup_os_error(
        self, mock_create_backup, authenticated_client, tmp_path
    ) -> None:
        """POST /api/v1/backup returns 500 on disk error."""
        mock_create_backup.side_effect = OSError("Disk full")
        authenticated_client.app.state.db_path = tmp_path / "taggarr.db"

        response = authenticated_client.post("/api/v1/backup")

        assert response.status_code == 500
        assert "Backup creation failed" in response.json()["detail"]

    @patch("taggarr.api.routes.backups.create_backup")
    def test_create_backup_uses_config_fallback(
        self, mock_create_backup, authenticated_client, db_session: Session, tmp_path
    ) -> None:
        """POST /api/v1/backup falls back to Config table when no app state."""
        from taggarr.db.models import Config as ConfigModel

        db_session.add(ConfigModel(key="db.path", value=str(tmp_path / "custom.db")))
        db_session.commit()

        mock_create_backup.return_value = (str(tmp_path / "backup.zip"), 512)

        # Don't set app.state.db_path - force fallback
        response = authenticated_client.post("/api/v1/backup")

        assert response.status_code == 201


class TestRestoreBackupErrors:
    """Tests for error handling in POST /api/v1/backup/{id}/restore."""

    @patch("taggarr.api.routes.backups.restore_backup")
    def test_restore_backup_file_not_found(
        self, mock_restore, authenticated_client, db_session: Session, tmp_path
    ) -> None:
        """POST /api/v1/backup/{id}/restore returns 404 on FileNotFoundError."""
        backup_file = tmp_path / "backup.zip"
        backup_file.write_bytes(b"PK\x03\x04test")
        backup = create_backup_in_db(db_session, path=str(backup_file))

        mock_restore.side_effect = FileNotFoundError("File not found")
        authenticated_client.app.state.db_path = tmp_path / "taggarr.db"

        response = authenticated_client.post(f"/api/v1/backup/{backup.id}/restore")

        assert response.status_code == 404

    @patch("taggarr.api.routes.backups.restore_backup")
    def test_restore_backup_value_error(
        self, mock_restore, authenticated_client, db_session: Session, tmp_path
    ) -> None:
        """POST /api/v1/backup/{id}/restore returns 400 on ValueError."""
        backup_file = tmp_path / "backup.zip"
        backup_file.write_bytes(b"PK\x03\x04test")
        backup = create_backup_in_db(db_session, path=str(backup_file))

        mock_restore.side_effect = ValueError("Invalid backup format")
        authenticated_client.app.state.db_path = tmp_path / "taggarr.db"

        response = authenticated_client.post(f"/api/v1/backup/{backup.id}/restore")

        assert response.status_code == 400

    @patch("taggarr.api.routes.backups.restore_backup")
    def test_restore_backup_os_error(
        self, mock_restore, authenticated_client, db_session: Session, tmp_path
    ) -> None:
        """POST /api/v1/backup/{id}/restore returns 500 on OSError."""
        backup_file = tmp_path / "backup.zip"
        backup_file.write_bytes(b"PK\x03\x04test")
        backup = create_backup_in_db(db_session, path=str(backup_file))

        mock_restore.side_effect = OSError("Disk error")
        authenticated_client.app.state.db_path = tmp_path / "taggarr.db"

        response = authenticated_client.post(f"/api/v1/backup/{backup.id}/restore")

        assert response.status_code == 500

    @patch("taggarr.api.routes.backups.restore_backup")
    def test_restore_backup_uses_config_fallback(
        self, mock_restore, authenticated_client, db_session: Session, tmp_path
    ) -> None:
        """POST /api/v1/backup/{id}/restore falls back to Config table."""
        from taggarr.db.models import Config as ConfigModel

        db_session.add(ConfigModel(key="db.path", value=str(tmp_path / "custom.db")))
        db_session.commit()

        backup_file = tmp_path / "backup.zip"
        backup_file.write_bytes(b"PK\x03\x04test")
        backup = create_backup_in_db(db_session, path=str(backup_file))

        mock_restore.return_value = None

        # Don't set app.state.db_path - force fallback
        response = authenticated_client.post(f"/api/v1/backup/{backup.id}/restore")

        assert response.status_code == 200


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

    def test_download_backup_success(
        self, authenticated_client, db_session: Session, tmp_path
    ) -> None:
        """GET /api/v1/backup/{id}/download returns the backup file."""
        # Create actual backup file
        backup_file = tmp_path / "test_backup.zip"
        backup_file.write_bytes(b"PK\x03\x04test backup content")

        backup = create_backup_in_db(
            db_session,
            path=str(backup_file),
        )

        response = authenticated_client.get(f"/api/v1/backup/{backup.id}/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

    def test_download_backup_not_found(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/backup/{id}/download returns 404 for non-existent backup."""
        response = authenticated_client.get("/api/v1/backup/9999/download")

        assert response.status_code == 404

    def test_download_backup_file_missing(
        self, authenticated_client, db_session: Session
    ) -> None:
        """GET /api/v1/backup/{id}/download returns 404 if file is missing."""
        backup = create_backup_in_db(
            db_session,
            path="/nonexistent/backup.zip",
        )

        response = authenticated_client.get(f"/api/v1/backup/{backup.id}/download")

        assert response.status_code == 404
        assert "not found on disk" in response.json()["detail"]


class TestRestoreBackup:
    """Tests for POST /api/v1/backup/{id}/restore endpoint."""

    @patch("taggarr.api.routes.backups.restore_backup")
    def test_restore_backup_success(
        self, mock_restore, authenticated_client, db_session: Session, tmp_path
    ) -> None:
        """POST /api/v1/backup/{id}/restore restores from backup."""
        # Create actual backup file
        backup_file = tmp_path / "test_backup.zip"
        backup_file.write_bytes(b"PK\x03\x04test backup content")

        backup = create_backup_in_db(
            db_session,
            path=str(backup_file),
        )

        # Set up app state with db_path
        authenticated_client.app.state.db_path = tmp_path / "taggarr.db"

        response = authenticated_client.post(f"/api/v1/backup/{backup.id}/restore")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "restart" in data["message"].lower()

    def test_restore_backup_not_found(
        self, authenticated_client, db_session: Session
    ) -> None:
        """POST /api/v1/backup/{id}/restore returns 404 for non-existent backup."""
        response = authenticated_client.post("/api/v1/backup/9999/restore")

        assert response.status_code == 404

    def test_restore_backup_file_missing(
        self, authenticated_client, db_session: Session, tmp_path
    ) -> None:
        """POST /api/v1/backup/{id}/restore returns 404 if file is missing."""
        backup = create_backup_in_db(
            db_session,
            path="/nonexistent/backup.zip",
        )

        authenticated_client.app.state.db_path = tmp_path / "taggarr.db"

        response = authenticated_client.post(f"/api/v1/backup/{backup.id}/restore")

        assert response.status_code == 404
        assert "not found on disk" in response.json()["detail"]


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
