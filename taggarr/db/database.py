"""Database connection and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine for the given database URL.

    Args:
        url: SQLAlchemy database URL (e.g., "sqlite:///path/to/db.sqlite")

    Returns:
        SQLAlchemy Engine instance
    """
    return sa_create_engine(url)


@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    """Yield a database session with automatic cleanup.

    The session is committed on successful exit and rolled back on exception.
    The session is always closed after exiting the context.

    Args:
        engine: SQLAlchemy Engine to bind the session to

    Yields:
        SQLAlchemy Session instance
    """
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
