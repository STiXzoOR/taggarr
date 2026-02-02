"""Tests for ScanHandler."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import sessionmaker

from taggarr.db import History, Instance
from taggarr.db.models import Base
from taggarr.workers.handlers.scan import ScanHandler


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
    """Create a ScanHandler instance."""
    return ScanHandler(session_factory)


@pytest.fixture
def sonarr_instance(session_factory):
    """Create a test Sonarr instance."""
    with session_factory() as session:
        instance = Instance(
            name="test-sonarr",
            type="sonarr",
            url="http://localhost:8989",
            api_key="test-api-key",
            root_path="/media/tv",
            target_languages="eng,deu",
            tags='{"dub": "dub", "semi": "semi-dub", "wrong": "wrong-dub"}',
            quick_mode=0,
            enabled=1,
            require_original_default=0,
            notify_on_wrong_dub=1,
            notify_on_original_missing=1,
        )
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance.id


@pytest.fixture
def radarr_instance(session_factory):
    """Create a test Radarr instance."""
    with session_factory() as session:
        instance = Instance(
            name="test-radarr",
            type="radarr",
            url="http://localhost:7878",
            api_key="test-api-key",
            root_path="/media/movies",
            target_languages="eng",
            tags='{"dub": "dub", "semi": "semi-dub", "wrong": "wrong-dub"}',
            quick_mode=0,
            enabled=1,
            require_original_default=0,
            notify_on_wrong_dub=1,
            notify_on_original_missing=1,
        )
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance.id


class TestScanHandlerExecute:
    """Tests for ScanHandler.execute method."""

    def test_execute_requires_instance_id(self, handler) -> None:
        """execute() raises ValueError when instance_id is missing."""
        with pytest.raises(ValueError, match="instance_id is required"):
            run_async(handler.execute())

    def test_execute_raises_for_unknown_instance(self, handler) -> None:
        """execute() raises ValueError for non-existent instance."""
        with pytest.raises(ValueError, match="Instance 999 not found"):
            run_async(handler.execute(instance_id=999))

    def test_execute_skips_disabled_instance(
        self, handler, session_factory, sonarr_instance
    ) -> None:
        """execute() skips scan for disabled instance."""
        # Disable the instance
        with session_factory() as session:
            instance = session.query(Instance).get(sonarr_instance)
            instance.enabled = 0
            session.commit()

        # Should complete without error but do nothing
        run_async(handler.execute(instance_id=sonarr_instance))

        # No history should be recorded for skipped scan
        with session_factory() as session:
            history_count = session.query(History).count()
            assert history_count == 0

    def test_execute_sonarr_records_history(
        self, handler, session_factory, sonarr_instance
    ) -> None:
        """execute() records history for Sonarr scan."""
        with patch.object(handler, "_scan_sonarr", return_value=None):
            run_async(handler.execute(instance_id=sonarr_instance))

        with session_factory() as session:
            history = session.query(History).first()
            assert history is not None
            assert history.event_type == "scan"
            assert history.instance_id == sonarr_instance

    def test_execute_radarr_records_history(
        self, handler, session_factory, radarr_instance
    ) -> None:
        """execute() records history for Radarr scan."""
        with patch.object(handler, "_scan_radarr", return_value=None):
            run_async(handler.execute(instance_id=radarr_instance))

        with session_factory() as session:
            history = session.query(History).first()
            assert history is not None
            assert history.event_type == "scan"
            assert history.instance_id == radarr_instance

    def test_execute_raises_for_unknown_type(
        self, handler, session_factory, sonarr_instance
    ) -> None:
        """execute() raises ValueError for unknown instance type."""
        # Change instance type to unknown
        with session_factory() as session:
            instance = session.query(Instance).get(sonarr_instance)
            instance.type = "unknown"
            session.commit()

        with pytest.raises(ValueError, match="Unknown instance type"):
            run_async(handler.execute(instance_id=sonarr_instance))


class TestScanHandlerSonarr:
    """Tests for Sonarr-specific scanning."""

    def test_scan_sonarr_creates_client(
        self, handler, session_factory, sonarr_instance
    ) -> None:
        """_scan_sonarr creates SonarrClient with correct config."""
        with patch(
            "taggarr.services.sonarr.SonarrClient"
        ) as mock_client_class:
            with session_factory() as session:
                instance = session.query(Instance).get(sonarr_instance)
                run_async(handler._scan_sonarr(session, instance))

            mock_client_class.assert_called_once_with(
                "http://localhost:8989", "test-api-key"
            )


class TestScanHandlerRadarr:
    """Tests for Radarr-specific scanning."""

    def test_scan_radarr_creates_client(
        self, handler, session_factory, radarr_instance
    ) -> None:
        """_scan_radarr creates RadarrClient with correct config."""
        with patch(
            "taggarr.services.radarr.RadarrClient"
        ) as mock_client_class:
            with session_factory() as session:
                instance = session.query(Instance).get(radarr_instance)
                run_async(handler._scan_radarr(session, instance))

            mock_client_class.assert_called_once_with(
                "http://localhost:7878", "test-api-key"
            )
