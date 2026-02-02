"""Tests for BackupHandler."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import sessionmaker

from taggarr.db import Backup
from taggarr.db.models import Base
from taggarr.workers.handlers.backup import BackupHandler


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@pytest.fixture
def db_engine(tmp_path: Path):
    """Create a temporary SQLite database engine."""
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    engine = sa_create_engine(url)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(db_engine):
    """Create a session factory for the test database."""
    return sessionmaker(bind=db_engine)


@pytest.fixture
def handler(session_factory):
    """Create a BackupHandler instance."""
    return BackupHandler(session_factory)


class TestBackupHandlerExecute:
    """Tests for BackupHandler.execute method."""

    def test_execute_creates_backup_record(
        self, handler, session_factory, tmp_path
    ) -> None:
        """execute() creates a new backup record."""
        # Use a separate file for the "database to backup" vs the test database
        source_db = tmp_path / "source.db"
        source_db.write_text("test database content")
        backup_dir = tmp_path / "backups"

        with patch(
            "taggarr.backup.operations.create_backup"
        ) as mock_create:
            mock_create.return_value = (str(backup_dir / "backup.zip"), 1024)

            run_async(
                handler.execute(
                    db_path=str(source_db), backup_dir=str(backup_dir)
                )
            )

        with session_factory() as session:
            backup = session.query(Backup).first()
            assert backup is not None
            assert backup.type == "manual"
            assert backup.size_bytes == 1024

    def test_execute_updates_existing_backup(
        self, handler, session_factory, tmp_path
    ) -> None:
        """execute() updates existing backup record when backup_id provided."""
        source_db = tmp_path / "source.db"
        source_db.write_text("test database content")
        backup_dir = tmp_path / "backups"

        # Create existing backup record
        from datetime import datetime, timezone

        with session_factory() as session:
            backup = Backup(
                filename="existing_backup.zip",
                path="",
                type="scheduled",
                size_bytes=0,
                created_at=datetime.now(timezone.utc),
            )
            session.add(backup)
            session.commit()
            backup_id = backup.id

        with patch(
            "taggarr.backup.operations.create_backup"
        ) as mock_create:
            mock_create.return_value = (str(backup_dir / "backup.zip"), 2048)

            run_async(
                handler.execute(
                    backup_id=backup_id,
                    db_path=str(source_db),
                    backup_dir=str(backup_dir),
                )
            )

        with session_factory() as session:
            backup = session.query(Backup).get(backup_id)
            assert backup.size_bytes == 2048

    def test_execute_raises_for_unknown_backup_id(
        self, handler, tmp_path
    ) -> None:
        """execute() raises ValueError for non-existent backup_id."""
        with pytest.raises(ValueError, match="Backup 999 not found"):
            run_async(handler.execute(backup_id=999))

    def test_execute_handles_backup_failure(
        self, handler, session_factory, tmp_path
    ) -> None:
        """execute() marks backup as failed on error."""
        source_db = tmp_path / "source.db"
        source_db.write_text("test database content")
        backup_dir = tmp_path / "backups"

        with patch(
            "taggarr.backup.operations.create_backup"
        ) as mock_create:
            mock_create.side_effect = OSError("Disk full")

            with pytest.raises(OSError, match="Disk full"):
                run_async(
                    handler.execute(
                        db_path=str(source_db), backup_dir=str(backup_dir)
                    )
                )

        with session_factory() as session:
            backup = session.query(Backup).first()
            assert backup is not None
            assert backup.size_bytes == -1  # Indicates failure

    def test_execute_creates_backup_directory(
        self, handler, session_factory, tmp_path
    ) -> None:
        """execute() creates backup directory if it doesn't exist."""
        source_db = tmp_path / "source.db"
        source_db.write_text("test database content")
        backup_dir = tmp_path / "new_backup_dir"

        assert not backup_dir.exists()

        with patch(
            "taggarr.backup.operations.create_backup"
        ) as mock_create:
            mock_create.return_value = (str(backup_dir / "backup.zip"), 512)

            run_async(
                handler.execute(
                    db_path=str(source_db), backup_dir=str(backup_dir)
                )
            )

        assert backup_dir.exists()

    def test_execute_uses_default_paths(
        self, handler, session_factory, tmp_path
    ) -> None:
        """execute() uses default paths when not specified."""
        with patch(
            "taggarr.backup.operations.create_backup"
        ) as mock_create:
            mock_create.return_value = ("./backups/backup.zip", 256)

            # Will use default paths ./taggarr.db and ./backups
            run_async(handler.execute())

            # Verify default paths were used
            call_args = mock_create.call_args
            assert str(call_args[0][0]) == "taggarr.db"  # default db_path
            assert str(call_args[0][1]) == "backups"  # default backup_dir

    def test_execute_logs_success(
        self, handler, session_factory, tmp_path, caplog
    ) -> None:
        """execute() logs success message."""
        import logging

        source_db = tmp_path / "source.db"
        source_db.write_text("test database content")
        backup_dir = tmp_path / "backups"

        with patch(
            "taggarr.backup.operations.create_backup"
        ) as mock_create:
            mock_create.return_value = (str(backup_dir / "backup.zip"), 512)

            with caplog.at_level(logging.INFO, logger="taggarr"):
                run_async(
                    handler.execute(
                        db_path=str(source_db), backup_dir=str(backup_dir)
                    )
                )

            # Check that success was logged
            assert any("Backup created" in record.message for record in caplog.records)
