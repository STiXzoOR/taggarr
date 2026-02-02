"""Tests for taggarr.server module."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from taggarr.server import _create_lifespan, create_server, run_server


class TestCreateServer:
    """Tests for create_server function."""

    def test_create_server_creates_app(self, tmp_path: Path) -> None:
        """create_server returns a FastAPI application."""
        db_path = tmp_path / "test.db"

        app = create_server(db_path=db_path)

        assert isinstance(app, FastAPI)

    def test_create_server_initializes_db(self, tmp_path: Path) -> None:
        """create_server initializes the database file."""
        db_path = tmp_path / "test.db"

        create_server(db_path=db_path)

        assert db_path.exists()

    def test_create_server_stores_engine_in_state(self, tmp_path: Path) -> None:
        """create_server stores database engine in app state."""
        from sqlalchemy import Engine

        db_path = tmp_path / "test.db"

        app = create_server(db_path=db_path)

        assert hasattr(app.state, "db_engine")
        assert isinstance(app.state.db_engine, Engine)

    def test_create_server_with_base_url(self, tmp_path: Path) -> None:
        """create_server configures base_url for reverse proxy."""
        db_path = tmp_path / "test.db"

        app = create_server(base_url="/taggarr", db_path=db_path)

        assert app.root_path == "/taggarr"

    def test_create_server_uses_default_db_path(self) -> None:
        """create_server uses default db path when not specified."""
        with patch("taggarr.server.create_engine") as mock_create_engine, \
             patch("taggarr.server.init_db"), \
             patch("taggarr.server.create_app") as mock_create_app:
            mock_app = MagicMock(spec=FastAPI)
            mock_app.state = MagicMock()
            mock_create_app.return_value = mock_app

            create_server()

            # Check that the default path was used
            call_args = mock_create_engine.call_args[0][0]
            assert "taggarr.db" in call_args


class TestRunServer:
    """Tests for run_server function."""

    def test_run_server_calls_uvicorn(self, tmp_path: Path) -> None:
        """run_server starts uvicorn with correct parameters."""
        db_path = tmp_path / "test.db"

        with patch("taggarr.server.uvicorn.run") as mock_uvicorn_run:
            run_server(
                host="127.0.0.1",
                port=9000,
                base_url="/api",
                db_path=db_path,
                reload=True,
            )

            mock_uvicorn_run.assert_called_once()
            call_kwargs = mock_uvicorn_run.call_args[1]
            assert call_kwargs["host"] == "127.0.0.1"
            assert call_kwargs["port"] == 9000
            assert call_kwargs["reload"] is True

    def test_run_server_uses_defaults(self) -> None:
        """run_server uses default values."""
        with patch("taggarr.server.uvicorn.run") as mock_uvicorn_run, \
             patch("taggarr.server.create_engine"), \
             patch("taggarr.server.init_db"), \
             patch("taggarr.server.create_app") as mock_create_app:
            mock_app = MagicMock(spec=FastAPI)
            mock_app.state = MagicMock()
            mock_create_app.return_value = mock_app

            run_server()

            mock_uvicorn_run.assert_called_once()
            call_kwargs = mock_uvicorn_run.call_args[1]
            assert call_kwargs["host"] == "0.0.0.0"
            assert call_kwargs["port"] == 8080
            assert call_kwargs["reload"] is False


class TestLifespan:
    """Tests for worker lifecycle management."""

    def test_lifespan_starts_and_stops_workers(self, tmp_path: Path) -> None:
        """Lifespan creates workers and stops them on shutdown."""
        from sqlalchemy import create_engine as sa_create_engine

        from taggarr.db.models import Base

        db_path = tmp_path / "test.db"
        engine = sa_create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        with patch("taggarr.server.CommandProcessor") as mock_cp, \
             patch("taggarr.server.ScanScheduler") as mock_ss, \
             patch("taggarr.server.BackupScheduler") as mock_bs:
            # Make start() return a coroutine that completes immediately
            mock_cp_instance = MagicMock()
            mock_cp_instance.start = AsyncMock()
            mock_cp.return_value = mock_cp_instance

            mock_ss_instance = MagicMock()
            mock_ss_instance.start = AsyncMock()
            mock_ss.return_value = mock_ss_instance

            mock_bs_instance = MagicMock()
            mock_bs_instance.start = AsyncMock()
            mock_bs.return_value = mock_bs_instance

            lifespan = _create_lifespan(engine, db_path)
            app = MagicMock(spec=FastAPI)
            app.state = MagicMock()

            async def run_lifespan():
                async with lifespan(app):
                    # Workers should be started
                    pass  # Exit immediately to trigger shutdown

            asyncio.run(run_lifespan())

            # Verify workers were instantiated
            mock_cp.assert_called_once()
            mock_ss.assert_called_once()
            mock_bs.assert_called_once()

            # Verify stop() was called on all workers
            mock_cp_instance.stop.assert_called_once()
            mock_ss_instance.stop.assert_called_once()
            mock_bs_instance.stop.assert_called_once()

    def test_lifespan_sets_app_state(self, tmp_path: Path) -> None:
        """Lifespan sets startup_time and db_path in app state."""
        from sqlalchemy import create_engine as sa_create_engine

        from taggarr.db.models import Base

        db_path = tmp_path / "test.db"
        engine = sa_create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        with patch("taggarr.server.CommandProcessor") as mock_cp, \
             patch("taggarr.server.ScanScheduler") as mock_ss, \
             patch("taggarr.server.BackupScheduler") as mock_bs:
            mock_cp_instance = MagicMock()
            mock_cp_instance.start = AsyncMock()
            mock_cp.return_value = mock_cp_instance

            mock_ss_instance = MagicMock()
            mock_ss_instance.start = AsyncMock()
            mock_ss.return_value = mock_ss_instance

            mock_bs_instance = MagicMock()
            mock_bs_instance.start = AsyncMock()
            mock_bs.return_value = mock_bs_instance

            lifespan = _create_lifespan(engine, db_path)
            app = FastAPI()  # Use real FastAPI to test state

            startup_time_set = None
            db_path_set = None

            async def run_lifespan():
                nonlocal startup_time_set, db_path_set
                async with lifespan(app):
                    startup_time_set = app.state.startup_time
                    db_path_set = app.state.db_path

            asyncio.run(run_lifespan())

            assert startup_time_set is not None
            assert isinstance(startup_time_set, datetime)
            assert db_path_set == db_path
