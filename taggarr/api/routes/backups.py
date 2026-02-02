"""Backup routes for taggarr API."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.backup.operations import create_backup, restore_backup
from taggarr.db import Backup, Config, User

router = APIRouter(prefix="/api/v1", tags=["backups"])


class BackupResponse(BaseModel):
    """Backup response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    size: int
    type: str
    created_at: datetime


def backup_to_response(backup: Backup) -> BackupResponse:
    """Convert Backup model to response."""
    return BackupResponse(
        id=backup.id,
        filename=backup.filename,
        size=backup.size_bytes or 0,
        type=backup.type,
        created_at=backup.created_at,
    )


@router.get("/backup", response_model=list[BackupResponse])
async def list_backups(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BackupResponse]:
    """List all backups.

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        List of all backups.
    """
    backups = db.query(Backup).order_by(Backup.created_at.desc()).all()
    return [backup_to_response(b) for b in backups]


@router.post("/backup", response_model=BackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup_endpoint(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BackupResponse:
    """Create a new backup.

    Creates the backup file and stores a record in the database.

    Args:
        request: FastAPI request to access app state.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Created backup record.
    """
    # Get database path
    db_path = getattr(request.app.state, "db_path", None)
    if db_path is None:
        config = db.query(Config).filter(Config.key == "db.path").first()
        db_path = Path(config.value) if config else Path("./taggarr.db")

    # Get backup directory
    config = db.query(Config).filter(Config.key == "backup.directory").first()
    backup_dir = Path(config.value) if config else Path("./backups")

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"taggarr_backup_{timestamp}.zip"

    try:
        path, size = create_backup(db_path, backup_dir)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database file not found: {e}",
        )
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup creation failed: {e}",
        )

    backup = Backup(
        filename=filename,
        path=path,
        type="manual",
        size_bytes=size,
        created_at=now,
    )
    db.add(backup)
    db.commit()
    db.refresh(backup)

    return backup_to_response(backup)


@router.delete("/backup/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    backup_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a backup.

    Args:
        backup_id: ID of the backup to delete.
        user: Current authenticated user.
        db: Database session.

    Raises:
        HTTPException: If backup not found.
    """
    backup = db.query(Backup).filter(Backup.id == backup_id).first()

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found",
        )

    db.delete(backup)
    db.commit()


@router.get("/backup/{backup_id}/download")
async def download_backup(
    backup_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download a backup file.

    Args:
        backup_id: ID of the backup to download.
        user: Current authenticated user.
        db: Database session.

    Returns:
        FileResponse containing the backup ZIP file.

    Raises:
        HTTPException: If backup not found or file doesn't exist.
    """
    backup = db.query(Backup).filter(Backup.id == backup_id).first()

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found",
        )

    backup_path = Path(backup.path)
    if not backup_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found on disk",
        )

    return FileResponse(
        path=backup_path,
        filename=backup.filename,
        media_type="application/zip",
    )


class RestoreResponse(BaseModel):
    """Response for backup restore operation."""

    success: bool
    message: str


@router.post("/backup/{backup_id}/restore", response_model=RestoreResponse)
async def restore_backup_endpoint(
    backup_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RestoreResponse:
    """Restore from a backup.

    WARNING: This will replace the current database with the backup.
    The application should be restarted after restore.

    Args:
        backup_id: ID of the backup to restore from.
        request: FastAPI request to access app state.
        user: Current authenticated user.
        db: Database session.

    Returns:
        RestoreResponse indicating success or failure.

    Raises:
        HTTPException: If backup not found or restore fails.
    """
    backup = db.query(Backup).filter(Backup.id == backup_id).first()

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found",
        )

    backup_path = Path(backup.path)
    if not backup_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found on disk",
        )

    # Get database path
    db_path = getattr(request.app.state, "db_path", None)
    if db_path is None:
        config = db.query(Config).filter(Config.key == "db.path").first()
        db_path = Path(config.value) if config else Path("./taggarr.db")

    try:
        restore_backup(backup_path, db_path)
        return RestoreResponse(
            success=True,
            message="Backup restored successfully. Please restart the application.",
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {e}",
        )
