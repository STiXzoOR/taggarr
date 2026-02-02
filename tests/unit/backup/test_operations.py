"""Tests for backup operations module."""

import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from taggarr.backup.operations import (
    create_backup,
    delete_backup,
    list_backups,
    restore_backup,
)


class TestCreateBackup:
    """Tests for create_backup function."""

    def test_create_backup_creates_zip(self, tmp_path: Path) -> None:
        """create_backup creates a ZIP file."""
        db_path = tmp_path / "test.db"
        db_path.write_text("test database content")
        backup_dir = tmp_path / "backups"

        path, size = create_backup(db_path, backup_dir)

        assert Path(path).exists()
        assert path.endswith(".zip")
        assert size > 0

    def test_create_backup_contains_database(self, tmp_path: Path) -> None:
        """create_backup includes database in ZIP."""
        db_path = tmp_path / "test.db"
        db_path.write_text("test database content")
        backup_dir = tmp_path / "backups"

        path, _ = create_backup(db_path, backup_dir)

        with zipfile.ZipFile(path, "r") as zf:
            assert "taggarr.db" in zf.namelist()
            content = zf.read("taggarr.db").decode()
            assert content == "test database content"

    def test_create_backup_uses_compression(self, tmp_path: Path) -> None:
        """create_backup uses DEFLATE compression."""
        db_path = tmp_path / "test.db"
        # Create a large file that should compress well
        db_path.write_text("A" * 10000)
        backup_dir = tmp_path / "backups"

        path, size = create_backup(db_path, backup_dir)

        # Compressed size should be much smaller than original
        assert size < 10000

    def test_create_backup_creates_directory(self, tmp_path: Path) -> None:
        """create_backup creates backup directory if needed."""
        db_path = tmp_path / "test.db"
        db_path.write_text("test")
        backup_dir = tmp_path / "new" / "backup" / "dir"

        assert not backup_dir.exists()

        create_backup(db_path, backup_dir)

        assert backup_dir.exists()

    def test_create_backup_raises_for_missing_db(self, tmp_path: Path) -> None:
        """create_backup raises FileNotFoundError for missing database."""
        db_path = tmp_path / "nonexistent.db"
        backup_dir = tmp_path / "backups"

        with pytest.raises(FileNotFoundError, match="Database file not found"):
            create_backup(db_path, backup_dir)

    def test_create_backup_uses_timestamp(self, tmp_path: Path) -> None:
        """create_backup includes timestamp in filename."""
        db_path = tmp_path / "test.db"
        db_path.write_text("test")
        backup_dir = tmp_path / "backups"

        path, _ = create_backup(db_path, backup_dir)

        filename = Path(path).name
        assert filename.startswith("taggarr_backup_")
        assert filename.endswith(".zip")


class TestRestoreBackup:
    """Tests for restore_backup function."""

    def test_restore_backup_extracts_database(self, tmp_path: Path) -> None:
        """restore_backup extracts database from ZIP."""
        # Create a backup
        backup_path = tmp_path / "backup.zip"
        with zipfile.ZipFile(backup_path, "w") as zf:
            zf.writestr("taggarr.db", "restored content")

        db_path = tmp_path / "restored.db"

        restore_backup(backup_path, db_path)

        assert db_path.exists()
        assert db_path.read_text() == "restored content"

    def test_restore_backup_creates_backup_of_existing(
        self, tmp_path: Path
    ) -> None:
        """restore_backup backs up existing database."""
        # Create existing database
        db_path = tmp_path / "taggarr.db"
        db_path.write_text("original content")

        # Create backup to restore from
        backup_path = tmp_path / "backup.zip"
        with zipfile.ZipFile(backup_path, "w") as zf:
            zf.writestr("taggarr.db", "restored content")

        restore_backup(backup_path, db_path)

        # Original should be backed up
        backup_of_original = tmp_path / "taggarr.db.bak"
        assert backup_of_original.exists()
        assert backup_of_original.read_text() == "original content"

        # Database should be restored
        assert db_path.read_text() == "restored content"

    def test_restore_backup_raises_for_missing_file(
        self, tmp_path: Path
    ) -> None:
        """restore_backup raises FileNotFoundError for missing backup."""
        backup_path = tmp_path / "nonexistent.zip"
        db_path = tmp_path / "taggarr.db"

        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            restore_backup(backup_path, db_path)

    def test_restore_backup_raises_for_invalid_backup(
        self, tmp_path: Path
    ) -> None:
        """restore_backup raises ValueError for invalid backup."""
        # Create ZIP without taggarr.db
        backup_path = tmp_path / "backup.zip"
        with zipfile.ZipFile(backup_path, "w") as zf:
            zf.writestr("other_file.txt", "not a database")

        db_path = tmp_path / "taggarr.db"

        with pytest.raises(ValueError, match="does not contain taggarr.db"):
            restore_backup(backup_path, db_path)


class TestListBackups:
    """Tests for list_backups function."""

    def test_list_backups_returns_empty_for_missing_dir(
        self, tmp_path: Path
    ) -> None:
        """list_backups returns empty list for non-existent directory."""
        backup_dir = tmp_path / "nonexistent"

        result = list_backups(backup_dir)

        assert result == []

    def test_list_backups_returns_backup_info(self, tmp_path: Path) -> None:
        """list_backups returns info about backup files."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create a backup file
        backup_path = backup_dir / "taggarr_backup_20240115_120000.zip"
        backup_path.write_text("backup content")

        result = list_backups(backup_dir)

        assert len(result) == 1
        assert result[0]["filename"] == "taggarr_backup_20240115_120000.zip"
        assert result[0]["path"] == str(backup_path)
        assert result[0]["size"] > 0

    def test_list_backups_ignores_non_backup_files(
        self, tmp_path: Path
    ) -> None:
        """list_backups ignores files that don't match pattern."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create non-backup files
        (backup_dir / "other_file.zip").write_text("not a backup")
        (backup_dir / "taggarr_backup.txt").write_text("not a zip")
        (backup_dir / "taggarr_backup_20240115_120000.zip").write_text(
            "real backup"
        )

        result = list_backups(backup_dir)

        assert len(result) == 1

    def test_list_backups_sorts_by_date(self, tmp_path: Path) -> None:
        """list_backups sorts backups newest first."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create backups with different timestamps
        import time

        old = backup_dir / "taggarr_backup_20240101_120000.zip"
        old.write_text("old")

        time.sleep(0.01)  # Ensure different mtime

        new = backup_dir / "taggarr_backup_20240115_120000.zip"
        new.write_text("new")

        result = list_backups(backup_dir)

        assert len(result) == 2
        assert "20240115" in result[0]["filename"]
        assert "20240101" in result[1]["filename"]


class TestDeleteBackup:
    """Tests for delete_backup function."""

    def test_delete_backup_removes_file(self, tmp_path: Path) -> None:
        """delete_backup removes the backup file."""
        backup_path = tmp_path / "backup.zip"
        backup_path.write_text("backup content")

        assert backup_path.exists()

        delete_backup(backup_path)

        assert not backup_path.exists()

    def test_delete_backup_raises_for_missing_file(
        self, tmp_path: Path
    ) -> None:
        """delete_backup raises FileNotFoundError for missing file."""
        backup_path = tmp_path / "nonexistent.zip"

        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            delete_backup(backup_path)
