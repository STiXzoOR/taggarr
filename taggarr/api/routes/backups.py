"""Backup routes for taggarr API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.db import Backup, User

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
async def create_backup(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BackupResponse:
    """Create a new backup.

    Creates a backup record. Actual file creation will be implemented
    in Phase 4 (Background Workers).

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        Created backup record.
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"taggarr_backup_{timestamp}.zip"
    path = f"/backups/{filename}"

    backup = Backup(
        filename=filename,
        path=path,
        type="manual",
        size_bytes=0,  # Will be updated when actual file is created
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
) -> None:
    """Download a backup file.

    Note: Not yet implemented. Actual file download will be implemented
    in Phase 4 (Background Workers).

    Args:
        backup_id: ID of the backup to download.
        user: Current authenticated user.
        db: Database session.

    Raises:
        HTTPException: Always raises 501 Not Implemented.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Backup download not yet implemented",
    )


@router.post("/backup/{backup_id}/restore")
async def restore_backup(
    backup_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Restore from a backup.

    Note: Not yet implemented. Actual restore functionality will be
    implemented in Phase 4 (Background Workers).

    Args:
        backup_id: ID of the backup to restore from.
        user: Current authenticated user.
        db: Database session.

    Raises:
        HTTPException: Always raises 501 Not Implemented.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Backup restore not yet implemented",
    )
