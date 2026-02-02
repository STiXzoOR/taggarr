"""Stats and system status routes for taggarr API."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.db import Backup, Command, History, Instance, Media, Tag, User

router = APIRouter(prefix="/api/v1", tags=["stats"])


class StatsResponse(BaseModel):
    """Aggregate statistics for dashboard."""

    total_media: int
    total_instances: int
    media_by_tag: dict[str, int]
    recent_scans: int
    pending_commands: int


class SystemStatusResponse(BaseModel):
    """System status information."""

    version: str
    uptime_seconds: int
    database_size_bytes: int
    last_backup: datetime | None


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatsResponse:
    """Get aggregate statistics for dashboard.

    Returns counts for media, instances, tags, recent scans, and pending commands.

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        Statistics response with aggregate counts.
    """
    # Count total media
    total_media = db.query(func.count(Media.id)).scalar() or 0

    # Count total instances
    total_instances = db.query(func.count(Instance.id)).scalar() or 0

    # Count media by tag
    media_by_tag = _count_media_by_tag(db)

    # Count recent scans (last 24 hours)
    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_scans = (
        db.query(func.count(History.id))
        .filter(
            History.event_type == "scan",
            History.date >= twenty_four_hours_ago,
        )
        .scalar()
        or 0
    )

    # Count pending commands (queued or started)
    pending_commands = (
        db.query(func.count(Command.id))
        .filter(Command.status.in_(["queued", "started"]))
        .scalar()
        or 0
    )

    return StatsResponse(
        total_media=total_media,
        total_instances=total_instances,
        media_by_tag=media_by_tag,
        recent_scans=recent_scans,
        pending_commands=pending_commands,
    )


def _count_media_by_tag(db: Session) -> dict[str, int]:
    """Count media grouped by tag label.

    Args:
        db: Database session.

    Returns:
        Dictionary with tag labels as keys and counts as values.
        Includes "dub", "semi-dub", "wrong-dub", and "untagged".
    """
    # Initialize counts with zeros for all expected tags
    counts = {
        "dub": 0,
        "semi-dub": 0,
        "wrong-dub": 0,
        "untagged": 0,
    }

    # Get counts for tagged media using a join
    tagged_counts = (
        db.query(Tag.label, func.count(Media.id))
        .join(Media, Media.tag_id == Tag.id)
        .group_by(Tag.label)
        .all()
    )

    for label, count in tagged_counts:
        if label in counts:
            counts[label] = count

    # Count untagged media (tag_id is NULL)
    untagged_count = (
        db.query(func.count(Media.id)).filter(Media.tag_id.is_(None)).scalar() or 0
    )
    counts["untagged"] = untagged_count

    return counts


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SystemStatusResponse:
    """Get system status information.

    Returns version, uptime, database size, and last backup time.
    Note: Uptime and database size are mocked for now.

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        System status response with version and health information.
    """
    from taggarr import __version__

    # Get most recent backup
    last_backup = (
        db.query(Backup)
        .order_by(Backup.created_at.desc())
        .first()
    )

    return SystemStatusResponse(
        version=__version__,
        uptime_seconds=0,  # Mocked for now - actual tracking in Phase 4
        database_size_bytes=0,  # Mocked for now
        last_backup=last_backup.created_at if last_backup else None,
    )
