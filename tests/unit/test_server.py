"""Tests for taggarr.server module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from taggarr.server import create_server, run_server


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
