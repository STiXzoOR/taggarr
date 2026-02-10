"""Tests for taggarr.workers.scan_scheduler module."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import sessionmaker

from taggarr.db.database import create_engine
from taggarr.db.models import Base, Command, Config, Instance
from taggarr.workers.scan_scheduler import ScanScheduler


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
    """Create a ScanScheduler instance."""
    return ScanScheduler(session_factory)


class TestSchedulerGetsIntervalFromConfig:
    """Tests for scheduler reading interval from config."""

    def test_scheduler_gets_interval_from_config(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should read scan interval from config table."""
        # Set up custom interval in config
        with session_factory() as session:
            config = Config(key="scan.interval", value="3600")
            session.add(config)
            session.commit()

        interval = scheduler._get_scan_interval()

        assert interval == 3600


class TestSchedulerUsesDefaultInterval:
    """Tests for scheduler using default interval."""

    def test_scheduler_uses_default_interval(self, scheduler, session_factory) -> None:
        """Scheduler should use 6 hours (21600 seconds) as default interval."""
        # No config set, should use default
        interval = scheduler._get_scan_interval()

        assert interval == 21600  # 6 hours in seconds


class TestSchedulerCreatesCommandsForEnabledInstances:
    """Tests for scheduler creating scan commands."""

    def test_scheduler_creates_commands_for_enabled_instances(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should create scan commands for all enabled instances."""
        # Create enabled instances
        with session_factory() as session:
            instance1 = Instance(
                name="sonarr-1",
                type="sonarr",
                url="http://sonarr1:8989",
                api_key="key1",
                root_path="/media/tv1",
                target_languages="en",
                tags="dub,semi-dub,wrong-dub",
                quick_mode=0,
                enabled=1,
                require_original_default=1,
                notify_on_wrong_dub=1,
                notify_on_original_missing=1,
            )
            instance2 = Instance(
                name="radarr-1",
                type="radarr",
                url="http://radarr1:7878",
                api_key="key2",
                root_path="/media/movies",
                target_languages="en,ja",
                tags="dub,semi-dub,wrong-dub",
                quick_mode=0,
                enabled=1,
                require_original_default=1,
                notify_on_wrong_dub=1,
                notify_on_original_missing=1,
            )
            session.add(instance1)
            session.add(instance2)
            session.commit()
            instance1_id = instance1.id
            instance2_id = instance2.id

        # Schedule scans
        scheduler._schedule_scans()

        # Verify commands were created
        with session_factory() as session:
            commands = session.query(Command).filter(Command.name == "ScanInstance").all()
            assert len(commands) == 2

            # Check command bodies contain correct instance IDs
            bodies = [cmd.body for cmd in commands]
            assert f'{{"instance_id": {instance1_id}}}' in bodies
            assert f'{{"instance_id": {instance2_id}}}' in bodies

            # Check command properties
            for cmd in commands:
                assert cmd.status == "Queued"
                assert cmd.trigger == "scheduled"
                assert cmd.queued_at is not None


class TestSchedulerIgnoresDisabledInstances:
    """Tests for scheduler ignoring disabled instances."""

    def test_scheduler_ignores_disabled_instances(
        self, scheduler, session_factory
    ) -> None:
        """Scheduler should not create commands for disabled instances."""
        # Create one enabled and one disabled instance
        with session_factory() as session:
            enabled_instance = Instance(
                name="enabled",
                type="sonarr",
                url="http://sonarr:8989",
                api_key="key1",
                root_path="/media/tv",
                target_languages="en",
                tags="dub,semi-dub,wrong-dub",
                quick_mode=0,
                enabled=1,
                require_original_default=1,
                notify_on_wrong_dub=1,
                notify_on_original_missing=1,
            )
            disabled_instance = Instance(
                name="disabled",
                type="radarr",
                url="http://radarr:7878",
                api_key="key2",
                root_path="/media/movies",
                target_languages="en",
                tags="dub,semi-dub,wrong-dub",
                quick_mode=0,
                enabled=0,  # Disabled
                require_original_default=1,
                notify_on_wrong_dub=1,
                notify_on_original_missing=1,
            )
            session.add(enabled_instance)
            session.add(disabled_instance)
            session.commit()
            enabled_id = enabled_instance.id

        # Schedule scans
        scheduler._schedule_scans()

        # Verify only one command was created
        with session_factory() as session:
            commands = session.query(Command).filter(Command.name == "ScanInstance").all()
            assert len(commands) == 1
            assert f'{{"instance_id": {enabled_id}}}' in commands[0].body


class TestSchedulerCanBeStopped:
    """Tests for scheduler stop functionality."""

    def test_scheduler_can_be_stopped(self, scheduler) -> None:
        """Scheduler should stop when stop() is called."""
        scheduler._running = True
        scheduler.stop()
        assert scheduler._running is False

    def test_scheduler_start_sets_running(self, scheduler) -> None:
        """start() should set _running to True."""
        loop_count = 0

        async def run_test():
            nonlocal loop_count

            async def mock_sleep(seconds):
                nonlocal loop_count
                loop_count += 1
                if loop_count >= 1:
                    scheduler.stop()

            with patch("taggarr.workers.scan_scheduler.asyncio.sleep", mock_sleep):
                await scheduler.start()

        run_async(run_test())

        # After stopping, _running should be False
        assert scheduler._running is False
        assert loop_count >= 1

    def test_scheduler_loops_until_stopped(self, scheduler, session_factory) -> None:
        """start() should continue running until stopped."""
        schedule_count = 0
        original_schedule = scheduler._schedule_scans

        def counting_schedule():
            nonlocal schedule_count
            schedule_count += 1
            if schedule_count >= 2:
                scheduler.stop()
            return original_schedule()

        scheduler._schedule_scans = counting_schedule

        async def run_test():
            async def fast_sleep(seconds):
                pass  # Don't actually sleep

            with patch("taggarr.workers.scan_scheduler.asyncio.sleep", fast_sleep):
                await scheduler.start()

        run_async(run_test())

        assert schedule_count >= 2


class TestSchedulerInit:
    """Tests for ScanScheduler initialization."""

    def test_init_stores_session_factory(self, session_factory) -> None:
        """ScanScheduler should store the session factory."""
        scheduler = ScanScheduler(session_factory)
        assert scheduler._session_factory is session_factory

    def test_init_sets_running_to_false(self, session_factory) -> None:
        """ScanScheduler should initialize with running=False."""
        scheduler = ScanScheduler(session_factory)
        assert scheduler._running is False
