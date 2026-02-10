"""FastAPI dependencies for taggarr API."""

from typing import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from taggarr.auth import is_session_expired
from taggarr.db import SessionModel, User, create_engine, get_session


def get_db(request: Request) -> Generator[Session, None, None]:
    """Get database session from app state.

    Uses the engine stored in app.state.db_engine if available,
    otherwise falls back to in-memory SQLite (for testing).

    Args:
        request: The incoming HTTP request.

    Yields:
        SQLAlchemy Session instance.
    """
    engine = getattr(request.app.state, "db_engine", None)
    if engine is None:  # pragma: no cover
        # Fallback for testing without server setup
        engine = create_engine("sqlite:///:memory:")

    with get_session(engine) as session:
        yield session


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from session cookie.

    Args:
        request: The incoming HTTP request.
        db: Database session.

    Returns:
        The authenticated User object.

    Raises:
        HTTPException: If not authenticated or session expired.
    """
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    session = (
        db.query(SessionModel)
        .filter(SessionModel.identifier == session_token)
        .first()
    )

    if not session or is_session_expired(session.expires_at.isoformat()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )

    return session.user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """Get current user if authenticated, None otherwise.

    Args:
        request: The incoming HTTP request.
        db: Database session.

    Returns:
        The authenticated User object or None.
    """
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None
