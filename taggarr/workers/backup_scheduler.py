"""Backup scheduler for taggarr."""

import asyncio
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy.orm import Session

from taggarr.db import Backup, Config


class BackupScheduler:
    """Schedules periodic backups."""

    def __init__(self, db_session_factory: Callable[[], Session]) -> None:
        """Initialize with a session factory callable.

        Args:
            db_session_factory: A callable that returns a database session.
        """
        self._session_factory = db_session_factory
        self._running = False

    async def start(self) -> None:
        """Start the scheduler."""
        self._running = True
        while self._running:
            interval = self._get_backup_interval()
            await asyncio.sleep(interval)
            if self._running:
                self._create_backup()
                self._apply_retention()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

    def _get_backup_interval(self) -> int:
        """Get backup interval from config (default 7 days in seconds).

        Returns:
            Backup interval in seconds.
        """
        with self._session_factory() as db:
            config = db.query(Config).filter(Config.key == "backup.interval").first()
            return int(config.value) if config else 604800  # 7 days

    def _get_retention_days(self) -> int:
        """Get retention period from config (default 28 days).

        Returns:
            Retention period in days.
        """
        with self._session_factory() as db:
            config = db.query(Config).filter(Config.key == "backup.retention").first()
            return int(config.value) if config else 28

    def _create_backup(self) -> None:
        """Create a scheduled backup record."""
        with self._session_factory() as db:
            now = datetime.utcnow()
            filename = f"taggarr_backup_{now.strftime('%Y%m%d_%H%M%S')}.zip"
            backup = Backup(
                filename=filename,
                path="",  # Will be updated when actual backup is created
                size_bytes=0,  # Will be updated when actual backup is created
                type="scheduled",
                created_at=now,
            )
            db.add(backup)
            db.commit()

    def _apply_retention(self) -> None:
        """Delete backups older than retention period."""
        with self._session_factory() as db:
            retention_days = self._get_retention_days()
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            # Only delete scheduled backups, keep manual ones
            db.query(Backup).filter(
                Backup.type == "scheduled",
                Backup.created_at < cutoff,
            ).delete()
            db.commit()
