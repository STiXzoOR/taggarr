"""Tag routes for taggarr API."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.db import Media, Tag, User

router = APIRouter(prefix="/api/v1", tags=["tags"])


class TagResponse(BaseModel):
    """Tag response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str


class TagWithCount(BaseModel):
    """Tag response model with media count."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    media_count: int


@router.get("/tag", response_model=list[TagWithCount])
async def list_tags(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TagWithCount]:
    """List all tags with media counts.

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        List of all tags with media counts.
    """
    # Query tags with their media counts using left outer join
    results = (
        db.query(Tag, func.count(Media.id).label("media_count"))
        .outerjoin(Media, Tag.id == Media.tag_id)
        .group_by(Tag.id)
        .all()
    )

    return [
        TagWithCount(
            id=tag.id,
            label=tag.label,
            media_count=count,
        )
        for tag, count in results
    ]


@router.get("/tag/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TagResponse:
    """Get tag by ID.

    Args:
        tag_id: ID of the tag to retrieve.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Tag details.

    Raises:
        HTTPException: If tag not found.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )

    return TagResponse(
        id=tag.id,
        label=tag.label,
    )
