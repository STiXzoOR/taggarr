"""Scan scheduler for taggarr."""

import asyncio
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from taggarr.db import Command, Config, Instance


class ScanScheduler:
    """Schedules periodic scans for instances."""

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
            interval = self._get_scan_interval()
            await asyncio.sleep(interval)
            if self._running:
                self._schedule_scans()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

    def _get_scan_interval(self) -> int:
        """Get scan interval from config (default 6 hours in seconds).

        Returns:
            Scan interval in seconds.
        """
        with self._session_factory() as db:
            config = db.query(Config).filter(Config.key == "scan.interval").first()
            return int(config.value) if config else 21600  # 6 hours

    def _schedule_scans(self) -> None:
        """Create scan commands for all enabled instances."""
        with self._session_factory() as db:
            instances = db.query(Instance).filter(Instance.enabled == 1).all()
            for instance in instances:
                command = Command(
                    name="ScanInstance",
                    body=f'{{"instance_id": {instance.id}}}',
                    status="Queued",
                    queued_at=datetime.now(timezone.utc),
                    trigger="scheduled",
                )
                db.add(command)
            db.commit()
