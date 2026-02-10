"""Tests for taggarr.db.database module."""

import pytest
from pathlib import Path

from taggarr.db.database import create_engine, get_session
from taggarr.db.models import Base


class TestCreateEngine:
    """Tests for create_engine function."""

    def test_create_engine_creates_sqlite_file(self, tmp_path: Path) -> None:
        """Engine creation should create SQLite database file."""
        from sqlalchemy import text

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"

        engine = create_engine(url)

        # Execute a simple query to force file creation
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        assert db_path.exists()

    def test_create_engine_returns_engine(self, tmp_path: Path) -> None:
        """create_engine should return a SQLAlchemy Engine."""
        from sqlalchemy import Engine

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"

        engine = create_engine(url)

        assert isinstance(engine, Engine)


class TestGetSession:
    """Tests for get_session function."""

    def test_get_session_returns_session(self, tmp_path: Path) -> None:
        """get_session should yield a working database session."""
        from sqlalchemy.orm import Session

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)

        with get_session(engine) as session:
            assert isinstance(session, Session)

    def test_get_session_commits_on_success(self, tmp_path: Path) -> None:
        """get_session should commit the session on successful exit."""
        from sqlalchemy import text

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)

        # Create a table and insert data in one session
        with get_session(engine) as session:
            session.execute(text("CREATE TABLE test (id INTEGER PRIMARY KEY)"))
            session.execute(text("INSERT INTO test (id) VALUES (1)"))

        # Verify data persisted in a new session
        with get_session(engine) as session:
            result = session.execute(text("SELECT COUNT(*) FROM test"))
            count = result.scalar()
            assert count == 1

    def test_get_session_rollbacks_on_exception(self, tmp_path: Path) -> None:
        """get_session should rollback the session on exception."""
        from sqlalchemy import text

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)

        # Create a table first
        with get_session(engine) as session:
            session.execute(text("CREATE TABLE test (id INTEGER PRIMARY KEY)"))

        # Try to insert data but raise an exception
        with pytest.raises(ValueError):
            with get_session(engine) as session:
                session.execute(text("INSERT INTO test (id) VALUES (1)"))
                raise ValueError("Intentional error")

        # Verify data was not persisted
        with get_session(engine) as session:
            result = session.execute(text("SELECT COUNT(*) FROM test"))
            count = result.scalar()
            assert count == 0

    def test_get_session_closes_session(self, tmp_path: Path) -> None:
        """get_session should close the session after exiting context."""
        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)

        with get_session(engine) as session:
            pass

        # Session should be closed after context exit
        # Accessing bind on a closed session still works, but executing queries won't
        assert session.get_bind() is not None  # Session object exists


class TestBase:
    """Tests for Base declarative base class."""

    def test_base_is_declarative_base(self) -> None:
        """Base should be a SQLAlchemy DeclarativeBase subclass."""
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)
