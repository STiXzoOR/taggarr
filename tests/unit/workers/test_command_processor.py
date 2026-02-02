"""Tests for taggarr.workers.command_processor module."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from taggarr.db.database import create_engine
from taggarr.db.models import Base, Command
from taggarr.workers.command_processor import CommandProcessor


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
def processor(session_factory):
    """Create a CommandProcessor instance."""
    return CommandProcessor(session_factory)


class TestCommandProcessorInit:
    """Tests for CommandProcessor initialization."""

    def test_init_stores_session_factory(self, session_factory) -> None:
        """CommandProcessor should store the session factory."""
        processor = CommandProcessor(session_factory)
        assert processor._session_factory is session_factory

    def test_init_sets_running_to_false(self, session_factory) -> None:
        """CommandProcessor should initialize with running=False."""
        processor = CommandProcessor(session_factory)
        assert processor._running is False


class TestProcessorPicksUpQueuedCommand:
    """Tests for processor picking up queued commands."""

    def test_processor_picks_up_queued_command(
        self, processor, session_factory
    ) -> None:
        """Processor should pick up and process a queued command."""
        # Create a queued command
        with session_factory() as session:
            command = Command(
                name="test_command",
                body='{"key": "value"}',
                status="Queued",
                queued_at=datetime.now(timezone.utc),
                trigger="manual",
            )
            session.add(command)
            session.commit()
            command_id = command.id

        # Process the command
        run_async(processor._process_next())

        # Verify it was processed
        with session_factory() as session:
            command = session.query(Command).get(command_id)
            assert command.status != "Queued"


class TestProcessorMarksCommandStarted:
    """Tests for processor marking commands as started."""

    def test_processor_marks_command_started(
        self, processor, session_factory
    ) -> None:
        """Processor should set status to Started before executing."""
        started_status = None

        # Capture status during execution
        original_execute = processor._execute

        async def capture_execute(name, body):
            nonlocal started_status
            with session_factory() as session:
                cmd = session.query(Command).filter(Command.name == name).first()
                started_status = cmd.status
            return await original_execute(name, body)

        processor._execute = capture_execute

        # Create a queued command
        with session_factory() as session:
            command = Command(
                name="test_started",
                body=None,
                status="Queued",
                queued_at=datetime.now(timezone.utc),
                trigger="manual",
            )
            session.add(command)
            session.commit()

        # Process
        run_async(processor._process_next())

        # Verify status was Started during execution
        assert started_status == "Started"

    def test_processor_sets_started_at_timestamp(
        self, processor, session_factory
    ) -> None:
        """Processor should set started_at when starting a command."""
        with session_factory() as session:
            command = Command(
                name="test_timestamp",
                body=None,
                status="Queued",
                queued_at=datetime.now(timezone.utc),
                trigger="manual",
            )
            session.add(command)
            session.commit()
            command_id = command.id

        before = datetime.now(timezone.utc)
        run_async(processor._process_next())
        after = datetime.now(timezone.utc)

        with session_factory() as session:
            command = session.query(Command).get(command_id)
            assert command.started_at is not None
            # Compare without timezone info since DB stores naive datetime
            assert before.replace(tzinfo=None) <= command.started_at <= after.replace(
                tzinfo=None
            )


class TestProcessorMarksCommandCompleted:
    """Tests for processor marking commands as completed."""

    def test_processor_marks_command_completed(
        self, processor, session_factory
    ) -> None:
        """Processor should set status to Completed after successful execution."""
        with session_factory() as session:
            command = Command(
                name="test_complete",
                body=None,
                status="Queued",
                queued_at=datetime.now(timezone.utc),
                trigger="manual",
            )
            session.add(command)
            session.commit()
            command_id = command.id

        run_async(processor._process_next())

        with session_factory() as session:
            command = session.query(Command).get(command_id)
            assert command.status == "Completed"

    def test_processor_sets_ended_at_timestamp(
        self, processor, session_factory
    ) -> None:
        """Processor should set ended_at when completing a command."""
        with session_factory() as session:
            command = Command(
                name="test_ended_at",
                body=None,
                status="Queued",
                queued_at=datetime.now(timezone.utc),
                trigger="manual",
            )
            session.add(command)
            session.commit()
            command_id = command.id

        before = datetime.now(timezone.utc)
        run_async(processor._process_next())
        after = datetime.now(timezone.utc)

        with session_factory() as session:
            command = session.query(Command).get(command_id)
            assert command.ended_at is not None
            # Compare without timezone info since DB stores naive datetime
            assert before.replace(tzinfo=None) <= command.ended_at <= after.replace(
                tzinfo=None
            )


class TestProcessorHandlesErrors:
    """Tests for processor error handling."""

    def test_processor_handles_errors(self, processor, session_factory) -> None:
        """Processor should set status to Failed on exception."""

        async def failing_execute(name, body):
            raise ValueError("Test error message")

        processor._execute = failing_execute

        with session_factory() as session:
            command = Command(
                name="test_fail",
                body=None,
                status="Queued",
                queued_at=datetime.now(timezone.utc),
                trigger="manual",
            )
            session.add(command)
            session.commit()
            command_id = command.id

        run_async(processor._process_next())

        with session_factory() as session:
            command = session.query(Command).get(command_id)
            assert command.status == "Failed"

    def test_processor_stores_exception_message(
        self, processor, session_factory
    ) -> None:
        """Processor should store exception message on failure."""

        async def failing_execute(name, body):
            raise ValueError("Test error message")

        processor._execute = failing_execute

        with session_factory() as session:
            command = Command(
                name="test_exception",
                body=None,
                status="Queued",
                queued_at=datetime.now(timezone.utc),
                trigger="manual",
            )
            session.add(command)
            session.commit()
            command_id = command.id

        run_async(processor._process_next())

        with session_factory() as session:
            command = session.query(Command).get(command_id)
            assert command.exception == "Test error message"

    def test_processor_sets_ended_at_on_failure(
        self, processor, session_factory
    ) -> None:
        """Processor should set ended_at even on failure."""

        async def failing_execute(name, body):
            raise RuntimeError("Failed")

        processor._execute = failing_execute

        with session_factory() as session:
            command = Command(
                name="test_fail_ended_at",
                body=None,
                status="Queued",
                queued_at=datetime.now(timezone.utc),
                trigger="manual",
            )
            session.add(command)
            session.commit()
            command_id = command.id

        before = datetime.now(timezone.utc)
        run_async(processor._process_next())
        after = datetime.now(timezone.utc)

        with session_factory() as session:
            command = session.query(Command).get(command_id)
            assert command.ended_at is not None
            # Compare without timezone info since DB stores naive datetime
            assert before.replace(tzinfo=None) <= command.ended_at <= after.replace(
                tzinfo=None
            )


class TestProcessorProcessesInOrder:
    """Tests for processor processing commands in order."""

    def test_processor_processes_in_order(self, processor, session_factory) -> None:
        """Processor should process commands in queued_at order (FIFO)."""
        processed_names = []
        original_execute = processor._execute

        async def tracking_execute(name, body):
            processed_names.append(name)
            return await original_execute(name, body)

        processor._execute = tracking_execute

        # Create commands with explicit ordering
        with session_factory() as session:
            cmd1 = Command(
                name="first",
                body=None,
                status="Queued",
                queued_at=datetime(2024, 1, 1, 10, 0, 0),
                trigger="manual",
            )
            cmd2 = Command(
                name="second",
                body=None,
                status="Queued",
                queued_at=datetime(2024, 1, 1, 10, 0, 1),
                trigger="manual",
            )
            cmd3 = Command(
                name="third",
                body=None,
                status="Queued",
                queued_at=datetime(2024, 1, 1, 10, 0, 2),
                trigger="manual",
            )
            # Add in non-chronological order to test sorting
            session.add(cmd3)
            session.add(cmd1)
            session.add(cmd2)
            session.commit()

        # Process all three
        async def process_all():
            await processor._process_next()
            await processor._process_next()
            await processor._process_next()

        run_async(process_all())

        assert processed_names == ["first", "second", "third"]


class TestProcessorCanBeStopped:
    """Tests for processor stop functionality."""

    def test_stop_sets_running_to_false(self, processor) -> None:
        """stop() should set _running to False."""
        processor._running = True
        processor.stop()
        assert processor._running is False

    def test_start_sets_running_to_true(self, processor) -> None:
        """start() should set _running to True."""

        async def run_test():
            # Schedule stop after a brief delay
            async def stop_soon():
                await asyncio.sleep(0.01)
                processor.stop()

            asyncio.create_task(stop_soon())
            await processor.start(poll_interval=0.001)

        run_async(run_test())

        # After stopping, _running should be False
        assert processor._running is False

    def test_start_loops_until_stopped(self, processor, session_factory) -> None:
        """start() should continue processing until stopped."""
        process_count = 0
        original_process = processor._process_next

        async def counting_process():
            nonlocal process_count
            process_count += 1
            if process_count >= 3:
                processor.stop()
            return await original_process()

        processor._process_next = counting_process

        run_async(processor.start(poll_interval=0.001))

        assert process_count >= 3


class TestProcessorNoCommands:
    """Tests for processor behavior when no commands are queued."""

    def test_process_next_with_no_commands(
        self, processor, session_factory
    ) -> None:
        """_process_next should handle empty queue gracefully."""
        # Should not raise an exception
        run_async(processor._process_next())

    def test_process_next_ignores_non_queued(
        self, processor, session_factory
    ) -> None:
        """_process_next should only pick up Queued commands."""
        with session_factory() as session:
            # Create commands with various statuses
            session.add(
                Command(
                    name="started",
                    body=None,
                    status="Started",
                    queued_at=datetime.now(timezone.utc),
                    trigger="manual",
                )
            )
            session.add(
                Command(
                    name="completed",
                    body=None,
                    status="Completed",
                    queued_at=datetime.now(timezone.utc),
                    trigger="manual",
                )
            )
            session.add(
                Command(
                    name="failed",
                    body=None,
                    status="Failed",
                    queued_at=datetime.now(timezone.utc),
                    trigger="manual",
                )
            )
            session.commit()

        executed_names = []
        original_execute = processor._execute

        async def tracking_execute(name, body):
            executed_names.append(name)
            return await original_execute(name, body)

        processor._execute = tracking_execute

        run_async(processor._process_next())

        # Nothing should be executed since no commands are Queued
        assert executed_names == []
