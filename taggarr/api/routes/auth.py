"""Authentication routes for taggarr API."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db, get_optional_user
from taggarr.auth import (
    create_session_token,
    get_session_expiry,
    hash_password,
    verify_password,
)
from taggarr.db import SessionModel, User

router = APIRouter(prefix="/api/v1", tags=["auth"])


class LoginRequest(BaseModel):
    """Request body for login endpoint."""

    username: str
    password: str


class InitializeRequest(BaseModel):
    """Request body for initialize endpoint."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Response model for user information."""

    username: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class StatusResponse(BaseModel):
    """Response model for auth status endpoint."""

    authenticated: bool
    user: UserResponse | None = None
    initialized: bool


@router.post("/auth/login")
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Login with username and password.

    Args:
        request: Login credentials.
        response: HTTP response for setting cookies.
        db: Database session.

    Returns:
        Success message.

    Raises:
        HTTPException: If credentials are invalid.
    """
    user = db.query(User).filter(User.username == request.username).first()

    if not user or not verify_password(
        request.password, user.password, user.salt, user.iterations
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Create session
    token = create_session_token()
    expires_at = get_session_expiry(hours=24)

    session = SessionModel(
        identifier=token,
        user_id=user.id,
        expires_at=datetime.fromisoformat(expires_at),
    )
    db.add(session)
    db.commit()

    # Set cookie
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=24 * 60 * 60,  # 24 hours
    )

    return {"message": "Login successful"}


@router.post("/auth/logout")
async def logout(
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Logout and invalidate session.

    Args:
        response: HTTP response for clearing cookies.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Success message.
    """
    # Delete all sessions for this user (simple approach)
    db.query(SessionModel).filter(SessionModel.user_id == user.id).delete()
    db.commit()

    response.delete_cookie("session")
    return {"message": "Logout successful"}


@router.get("/auth/status", response_model=StatusResponse)
async def auth_status(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    """Check authentication status.

    Args:
        user: Current user if authenticated.
        db: Database session.

    Returns:
        Authentication status with user info if authenticated.
    """
    # Check if system is initialized (has any users)
    initialized = db.query(User).first() is not None

    if user:
        return StatusResponse(
            authenticated=True,
            user=UserResponse(username=user.username),
            initialized=initialized,
        )
    return StatusResponse(
        authenticated=False,
        user=None,
        initialized=initialized,
    )


@router.post("/initialize")
async def initialize(
    request: InitializeRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Initialize system with first admin user.

    Args:
        request: Admin user credentials.
        response: HTTP response for setting cookies.
        db: Database session.

    Returns:
        Success message.

    Raises:
        HTTPException: If system is already initialized.
    """
    # Check if already initialized
    if db.query(User).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System already initialized",
        )

    # Create admin user
    password_hash, salt, iterations = hash_password(request.password)

    user = User(
        identifier=str(uuid.uuid4()),
        username=request.username,
        password=password_hash,
        salt=salt,
        iterations=iterations,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto-login after initialization
    token = create_session_token()
    expires_at = get_session_expiry(hours=24)

    session = SessionModel(
        identifier=token,
        user_id=user.id,
        expires_at=datetime.fromisoformat(expires_at),
    )
    db.add(session)
    db.commit()

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=24 * 60 * 60,
    )

    return {"message": "System initialized successfully"}
