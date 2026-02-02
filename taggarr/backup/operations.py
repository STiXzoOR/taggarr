"""Backup file operations for taggarr."""

import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("taggarr")


def create_backup(db_path: Path, backup_dir: Path) -> tuple[str, int]:
    """Create a ZIP backup of the database.

    Args:
        db_path: Path to the SQLite database file.
        backup_dir: Directory to store the backup.

    Returns:
        Tuple of (backup_path, size_bytes).

    Raises:
        FileNotFoundError: If the database file doesn't exist.
        OSError: If backup creation fails.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    # Ensure backup directory exists
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"taggarr_backup_{timestamp}.zip"
    backup_path = backup_dir / backup_filename

    logger.info(f"Creating backup: {backup_path}")

    # Create ZIP file with database
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add the database file with a consistent name inside the ZIP
        zf.write(db_path, "taggarr.db")

    size = backup_path.stat().st_size
    logger.info(f"Backup created: {backup_path} ({size} bytes)")

    return str(backup_path), size


def restore_backup(backup_path: Path, db_path: Path) -> None:
    """Restore database from a ZIP backup.

    Args:
        backup_path: Path to the backup ZIP file.
        db_path: Path where the database should be restored.

    Raises:
        FileNotFoundError: If the backup file doesn't exist.
        ValueError: If the backup doesn't contain the expected database file.
        OSError: If restoration fails.
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    logger.info(f"Restoring backup from: {backup_path}")

    # Verify backup contains the database
    with zipfile.ZipFile(backup_path, "r") as zf:
        if "taggarr.db" not in zf.namelist():
            raise ValueError("Backup does not contain taggarr.db")

    # Create backup of current database if it exists
    if db_path.exists():
        current_backup = db_path.with_suffix(".db.bak")
        logger.info(f"Backing up current database to: {current_backup}")
        shutil.copy2(db_path, current_backup)

    # Extract database from backup
    with zipfile.ZipFile(backup_path, "r") as zf:
        # Extract to temporary location first
        temp_path = db_path.with_suffix(".db.tmp")
        with zf.open("taggarr.db") as src, open(temp_path, "wb") as dst:
            shutil.copyfileobj(src, dst)

        # Move to final location (atomic on most filesystems)
        shutil.move(str(temp_path), str(db_path))

    logger.info(f"Backup restored to: {db_path}")


def list_backups(backup_dir: Path) -> list[dict]:
    """List all backup files in a directory.

    Args:
        backup_dir: Directory containing backup files.

    Returns:
        List of dictionaries with backup info (filename, path, size, created).
    """
    if not backup_dir.exists():
        return []

    backups = []
    for path in backup_dir.glob("taggarr_backup_*.zip"):
        stat = path.stat()
        backups.append(
            {
                "filename": path.name,
                "path": str(path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime),
            }
        )

    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x["created"], reverse=True)
    return backups


def delete_backup(backup_path: Path) -> None:
    """Delete a backup file.

    Args:
        backup_path: Path to the backup file to delete.

    Raises:
        FileNotFoundError: If the backup file doesn't exist.
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    backup_path.unlink()
    logger.info(f"Backup deleted: {backup_path}")
