"""Log routes for taggarr API."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from taggarr.api.deps import get_current_user
from taggarr.db import User

router = APIRouter(prefix="/api/v1", tags=["logs"])


class LogEntry(BaseModel):
    """A single log entry."""

    timestamp: datetime
    level: str  # "DEBUG", "INFO", "WARNING", "ERROR"
    message: str
    source: str | None = None


class LogsResponse(BaseModel):
    """Response containing log entries."""

    entries: list[LogEntry]
    total: int


class LogFile(BaseModel):
    """Information about a log file."""

    name: str
    size: int
    modified_at: datetime


@router.get("/log/file", response_model=list[LogFile])
async def list_log_files(
    user: User = Depends(get_current_user),
) -> list[LogFile]:
    """List available log files.

    Returns an empty list (stub implementation for Phase 3).
    Actual log file listing will be implemented in Phase 4.

    Args:
        user: Current authenticated user.

    Returns:
        List of log file information (empty for now).
    """
    return []


@router.get("/log/file/{name}")
async def download_log_file(
    name: str,
    user: User = Depends(get_current_user),
) -> None:
    """Download a specific log file.

    Returns 501 Not Implemented (stub implementation for Phase 3).
    Actual log file download will be implemented in Phase 4.

    Args:
        name: Name of the log file to download.
        user: Current authenticated user.

    Raises:
        HTTPException: 501 Not Implemented.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Log file download not implemented yet",
    )


@router.get("/log", response_model=LogsResponse)
async def get_logs(
    user: User = Depends(get_current_user),
) -> LogsResponse:
    """Get recent log entries.

    Returns an empty list (stub implementation for Phase 3).
    Actual log reading will be implemented in Phase 4.

    Args:
        user: Current authenticated user.

    Returns:
        LogsResponse with empty entries list and zero total.
    """
    return LogsResponse(entries=[], total=0)
