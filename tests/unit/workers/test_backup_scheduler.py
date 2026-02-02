"""Tests for taggarr.workers.backup_scheduler module."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from taggarr.db.database import create_engine
from taggarr.db.models import Backup, Base, Config
from taggarr.workers.backup_scheduler import BackupScheduler


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@pytest.fixture
def db_engine(tmp_path: Path):
    """Create a temporary in-memory database engine."""
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(db_engine):
    """Create a session factory for the test database."""
    return sessionmaker(bind=db_engine)


@pytest.fixture
def scheduler(session_factory):
    """Create a BackupScheduler instance."""
    return BackupScheduler(session_factory)


class TestBackupSchedulerInit:
    """Tests for BackupScheduler initialization."""

    def test_init_stores_session_factory(self, session_factory) -> None:
        """BackupScheduler should store the session factory."""
        scheduler = BackupScheduler(session_factory)
        assert scheduler._session_factory is session_factory

    def test_init_sets_running_to_false(self, session_factory) -> None:
        """BackupScheduler should initialize with running=False."""
        scheduler = BackupScheduler(session_factory)
        assert scheduler._running is False


class TestSchedulerGetsIntervalFromConfig:
    """Tests for scheduler reading backup interval from config."""

    def test_scheduler_gets_interval_from_config(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should read backup interval from config table."""
        # Set custom interval in config (1 day = 86400 seconds)
        with session_factory() as session:
            config = Config(key="backup.interval", value="86400")
            session.add(config)
            session.commit()

        interval = scheduler._get_backup_interval()
        assert interval == 86400


class TestSchedulerUsesDefaultInterval:
    """Tests for scheduler using default interval when not configured."""

    def test_scheduler_uses_default_interval(self, scheduler, session_factory) -> None:
        """Scheduler should use 7 days (604800 seconds) as default interval."""
        # No config set, should use default
        interval = scheduler._get_backup_interval()
        assert interval == 604800  # 7 days in seconds


class TestSchedulerCreatesBackupRecord:
    """Tests for scheduler creating backup records."""

    def test_scheduler_creates_backup_record(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should create a backup record in the database."""
        before = datetime.utcnow()
        scheduler._create_backup()
        after = datetime.utcnow()

        with session_factory() as session:
            backups = session.query(Backup).all()
            assert len(backups) == 1
            backup = backups[0]
            assert backup.type == "scheduled"
            assert backup.filename.startswith("taggarr_backup_")
            assert backup.filename.endswith(".zip")
            assert before <= backup.created_at <= after

    def test_scheduler_creates_backup_with_timestamp_filename(
        self, scheduler, session_factory
    ) -> None:
        """Backup filename should include timestamp."""
        scheduler._create_backup()

        with session_factory() as session:
            backup = session.query(Backup).first()
            # Filename format: taggarr_backup_YYYYMMDD_HHMMSS.zip
            assert backup.filename.startswith("taggarr_backup_20")  # Year starts with 20
            assert "_" in backup.filename

    def test_scheduler_creates_backup_with_empty_path(
        self, scheduler, session_factory
    ) -> None:
        """Backup should have empty path initially (filled when actual backup runs)."""
        scheduler._create_backup()

        with session_factory() as session:
            backup = session.query(Backup).first()
            assert backup.path == ""

    def test_scheduler_creates_backup_with_zero_size(
        self, scheduler, session_factory
    ) -> None:
        """Backup should have zero size initially (filled when actual backup runs)."""
        scheduler._create_backup()

        with session_factory() as session:
            backup = session.query(Backup).first()
            assert backup.size_bytes == 0


class TestSchedulerAppliesRetentionPolicy:
    """Tests for scheduler applying retention policy."""

    def test_scheduler_applies_retention_policy(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should delete scheduled backups older than retention period."""
        # Set retention to 28 days
        with session_factory() as session:
            config = Config(key="backup.retention", value="28")
            session.add(config)

            # Create old scheduled backup (30 days ago)
            old_backup = Backup(
                filename="old_backup.zip",
                path="/backups/old_backup.zip",
                type="scheduled",
                size_bytes=1000,
                created_at=datetime.utcnow() - timedelta(days=30),
            )
            session.add(old_backup)

            # Create recent scheduled backup (7 days ago)
            recent_backup = Backup(
                filename="recent_backup.zip",
                path="/backups/recent_backup.zip",
                type="scheduled",
                size_bytes=1000,
                created_at=datetime.utcnow() - timedelta(days=7),
            )
            session.add(recent_backup)
            session.commit()

        scheduler._apply_retention()

        with session_factory() as session:
            backups = session.query(Backup).all()
            assert len(backups) == 1
            assert backups[0].filename == "recent_backup.zip"

    def test_scheduler_uses_default_retention_period(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should use 28 days as default retention period."""
        retention = scheduler._get_retention_days()
        assert retention == 28


class TestSchedulerKeepsManualBackups:
    """Tests for scheduler keeping manual backups during retention."""

    def test_scheduler_keeps_manual_backups(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should not delete manual backups regardless of age."""
        with session_factory() as session:
            config = Config(key="backup.retention", value="28")
            session.add(config)

            # Create old manual backup (60 days ago)
            manual_backup = Backup(
                filename="manual_backup.zip",
                path="/backups/manual_backup.zip",
                type="manual",
                size_bytes=1000,
                created_at=datetime.utcnow() - timedelta(days=60),
            )
            session.add(manual_backup)

            # Create old scheduled backup (60 days ago)
            scheduled_backup = Backup(
                filename="scheduled_backup.zip",
                path="/backups/scheduled_backup.zip",
                type="scheduled",
                size_bytes=1000,
                created_at=datetime.utcnow() - timedelta(days=60),
            )
            session.add(scheduled_backup)
            session.commit()

        scheduler._apply_retention()

        with session_factory() as session:
            backups = session.query(Backup).all()
            assert len(backups) == 1
            assert backups[0].type == "manual"
            assert backups[0].filename == "manual_backup.zip"


class TestSchedulerCanBeStopped:
    """Tests for scheduler stop functionality."""

    def test_stop_sets_running_to_false(self, scheduler) -> None:
        """stop() should set _running to False."""
        scheduler._running = True
        scheduler.stop()
        assert scheduler._running is False

    def test_start_sets_running_to_true(self, scheduler, session_factory) -> None:
        """start() should set _running to True initially."""
        was_running = False

        # Override _get_backup_interval to capture running state and stop
        def capture_and_stop():
            nonlocal was_running
            was_running = scheduler._running
            scheduler.stop()
            return 0  # Immediate

        scheduler._get_backup_interval = capture_and_stop

        run_async(scheduler.start())

        assert was_running is True

    def test_scheduler_stops_on_stop_call(self, scheduler, session_factory) -> None:
        """Scheduler should exit start loop when stopped."""
        loop_count = 0

        # Override _get_backup_interval to control timing and count loops
        def counting_interval():
            nonlocal loop_count
            loop_count += 1
            if loop_count >= 2:
                scheduler.stop()
            return 0  # Immediate, no sleep delay

        scheduler._get_backup_interval = counting_interval

        run_async(scheduler.start())

        # Should have looped at least once before stopping
        assert loop_count >= 1


class TestSchedulerStartLoop:
    """Tests for scheduler main loop behavior."""

    def test_scheduler_creates_backup_after_interval(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should create backup after waiting interval."""
        backup_created = False

        original_create = scheduler._create_backup

        def tracking_create():
            nonlocal backup_created
            backup_created = True
            scheduler.stop()  # Stop after first backup
            return original_create()

        scheduler._create_backup = tracking_create
        # Use immediate interval
        scheduler._get_backup_interval = lambda: 0

        run_async(scheduler.start())

        assert backup_created

    def test_scheduler_applies_retention_after_backup(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should apply retention after creating backup."""
        operations = []

        original_create = scheduler._create_backup
        original_apply = scheduler._apply_retention

        def tracking_create():
            operations.append("create")
            scheduler.stop()
            return original_create()

        def tracking_apply():
            operations.append("retention")
            return original_apply()

        scheduler._create_backup = tracking_create
        scheduler._apply_retention = tracking_apply
        # Use immediate interval
        scheduler._get_backup_interval = lambda: 0

        run_async(scheduler.start())

        assert operations == ["create", "retention"]
