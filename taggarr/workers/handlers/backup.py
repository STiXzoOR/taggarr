"""Backup handler for creating database backups."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from taggarr.workers.handlers.base import BaseHandler

logger = logging.getLogger("taggarr")


class BackupHandler(BaseHandler):
    """Handler for CreateBackup commands."""

    async def execute(self, **kwargs: Any) -> None:
        """Execute a backup creation.

        Args:
            **kwargs: Optional parameters:
                - backup_id: ID of existing backup record to update
                - db_path: Path to the database file
                - backup_dir: Directory to store backups (default: ./backups)

        Raises:
            ValueError: If backup creation fails.
        """
        from taggarr.backup.operations import create_backup
        from taggarr.db import Backup

        backup_id = kwargs.get("backup_id")
        db_path = kwargs.get("db_path")
        backup_dir = kwargs.get("backup_dir", "./backups")

        # Ensure backup directory exists
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        with self._session_factory() as db:
            if backup_id:
                # Update existing backup record
                backup = db.query(Backup).filter(Backup.id == backup_id).first()
                if not backup:
                    raise ValueError(f"Backup {backup_id} not found")
            else:
                # Create new backup record
                now = datetime.now(timezone.utc)
                filename = f"taggarr_backup_{now.strftime('%Y%m%d_%H%M%S')}.zip"
                backup = Backup(
                    filename=filename,
                    path="",
                    type="manual",
                    size_bytes=0,
                    created_at=now,
                )
                db.add(backup)
                db.commit()
                db.refresh(backup)

            if db_path is None:
                # Try to find db_path from config
                from taggarr.db import Config

                config = db.query(Config).filter(Config.key == "db.path").first()
                if config:
                    db_path = config.value
                else:
                    db_path = "./taggarr.db"

            logger.info(f"Creating backup: {backup.filename}")

            try:
                # Create the actual backup
                path, size = create_backup(Path(db_path), backup_path)

                # Update backup record with actual values
                backup.path = path
                backup.size_bytes = size
                db.commit()

                logger.info(f"Backup created: {path} ({size} bytes)")
            except Exception as e:
                logger.error(f"Backup creation failed: {e}")
                # Mark backup as failed by setting negative size
                backup.size_bytes = -1
                db.commit()
                raise
