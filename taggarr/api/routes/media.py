"""Media management routes for taggarr API."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.db import History, Instance, Media, Season, Tag, User

router = APIRouter(prefix="/api/v1", tags=["media"])


class SeasonResponse(BaseModel):
    """Season response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    media_id: int
    season_number: int
    episode_count: int
    status: str | None
    original_dub: list[str] | None
    dub: list[str] | None
    missing_dub: list[str] | None
    unexpected_languages: list[str] | None
    last_modified: int | None

    @field_validator(
        "original_dub", "dub", "missing_dub", "unexpected_languages", mode="before"
    )
    @classmethod
    def parse_json_list(cls, v: str | list[str] | None) -> list[str] | None:
        """Parse JSON string to list if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            return json.loads(v)
        return v


class MediaListItem(BaseModel):
    """Media item in list response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    instance_id: int
    title: str
    path: str
    media_type: str
    original_language: str | None
    tag_id: int | None
    added: datetime
    last_scanned: datetime | None
    override_require_original: bool | None
    override_notify: bool | None

    @field_validator("override_require_original", "override_notify", mode="before")
    @classmethod
    def parse_int_bool(cls, v: int | bool | None) -> bool | None:
        """Parse integer to boolean if needed."""
        if v is None:
            return None
        return bool(v)


class PaginatedMediaResponse(BaseModel):
    """Paginated list of media items."""

    items: list[MediaListItem]
    total: int
    page: int
    page_size: int


class MediaDetailResponse(BaseModel):
    """Detailed media response with seasons."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    instance_id: int
    instance_name: str
    title: str
    clean_title: str
    path: str
    media_type: str
    original_language: str | None
    tag_id: int | None
    tag_label: str | None
    added: datetime
    last_scanned: datetime | None
    last_modified: int | None
    override_require_original: bool | None
    override_notify: bool | None
    seasons: list[SeasonResponse]

    @field_validator("override_require_original", "override_notify", mode="before")
    @classmethod
    def parse_int_bool(cls, v: int | bool | None) -> bool | None:
        """Parse integer to boolean if needed."""
        if v is None:
            return None
        return bool(v)


class MediaUpdate(BaseModel):
    """Request to update media overrides."""

    override_require_original: bool | None = None
    override_notify: bool | None = None


class HistoryResponse(BaseModel):
    """History event response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: datetime
    event_type: str
    media_id: int | None
    instance_id: int | None
    data: dict | None

    @field_validator("data", mode="before")
    @classmethod
    def parse_json_data(cls, v: str | dict | None) -> dict | None:
        """Parse JSON string to dict if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            return json.loads(v)
        return v


def media_to_list_item(media: Media) -> MediaListItem:
    """Convert Media model to list item response."""
    return MediaListItem(
        id=media.id,
        instance_id=media.instance_id,
        title=media.title,
        path=media.path,
        media_type=media.media_type,
        original_language=media.original_language,
        tag_id=media.tag_id,
        added=media.added,
        last_scanned=media.last_scanned,
        override_require_original=media.override_require_original,
        override_notify=media.override_notify,
    )


def media_to_detail_response(media: Media) -> MediaDetailResponse:
    """Convert Media model to detail response."""
    return MediaDetailResponse(
        id=media.id,
        instance_id=media.instance_id,
        instance_name=media.instance.name if media.instance else "",
        title=media.title,
        clean_title=media.clean_title,
        path=media.path,
        media_type=media.media_type,
        original_language=media.original_language,
        tag_id=media.tag_id,
        tag_label=media.tag.label if media.tag else None,
        added=media.added,
        last_scanned=media.last_scanned,
        last_modified=media.last_modified,
        override_require_original=media.override_require_original,
        override_notify=media.override_notify,
        seasons=[season_to_response(s) for s in media.seasons],
    )


def season_to_response(season: Season) -> SeasonResponse:
    """Convert Season model to response."""
    return SeasonResponse(
        id=season.id,
        media_id=season.media_id,
        season_number=season.season_number,
        episode_count=season.episode_count,
        status=season.status,
        original_dub=season.original_dub,
        dub=season.dub,
        missing_dub=season.missing_dub,
        unexpected_languages=season.unexpected_languages,
        last_modified=season.last_modified,
    )


def history_to_response(history: History) -> HistoryResponse:
    """Convert History model to response."""
    return HistoryResponse(
        id=history.id,
        date=history.date,
        event_type=history.event_type,
        media_id=history.media_id,
        instance_id=history.instance_id,
        data=history.data,
    )


@router.get("/media", response_model=PaginatedMediaResponse)
async def list_media(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1),
    instance_id: Optional[int] = Query(default=None),
    tag_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedMediaResponse:
    """List media with pagination and filtering.

    Args:
        page: Page number (default 1).
        page_size: Number of items per page (default 25, max 100).
        instance_id: Filter by instance ID.
        tag_id: Filter by tag ID.
        search: Search by title (case-insensitive).
        user: Current authenticated user.
        db: Database session.

    Returns:
        Paginated list of media items.
    """
    # Cap page_size at 100
    page_size = min(page_size, 100)

    query = db.query(Media)

    # Apply filters
    if instance_id is not None:
        query = query.filter(Media.instance_id == instance_id)
    if tag_id is not None:
        query = query.filter(Media.tag_id == tag_id)
    if search:
        query = query.filter(Media.title.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    media_items = query.offset(offset).limit(page_size).all()

    return PaginatedMediaResponse(
        items=[media_to_list_item(m) for m in media_items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/media/{media_id}", response_model=MediaDetailResponse)
async def get_media(
    media_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MediaDetailResponse:
    """Get media details with seasons.

    Args:
        media_id: ID of the media to retrieve.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Media details with seasons.

    Raises:
        HTTPException: If media not found.
    """
    media = db.query(Media).filter(Media.id == media_id).first()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )

    return media_to_detail_response(media)


@router.put("/media/{media_id}", response_model=MediaDetailResponse)
async def update_media(
    media_id: int,
    request: MediaUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MediaDetailResponse:
    """Update media overrides.

    Args:
        media_id: ID of the media to update.
        request: Update request with overrides.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Updated media details.

    Raises:
        HTTPException: If media not found.
    """
    media = db.query(Media).filter(Media.id == media_id).first()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )

    # Update overrides - handle explicit None values
    update_data = request.model_dump(exclude_unset=False)

    if "override_require_original" in update_data:
        value = update_data["override_require_original"]
        if value is None:
            media.override_require_original = None
        else:
            media.override_require_original = 1 if value else 0

    if "override_notify" in update_data:
        value = update_data["override_notify"]
        if value is None:
            media.override_notify = None
        else:
            media.override_notify = 1 if value else 0

    db.commit()
    db.refresh(media)

    return media_to_detail_response(media)


@router.get("/media/{media_id}/history", response_model=list[HistoryResponse])
async def get_media_history(
    media_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HistoryResponse]:
    """Get history events for a media item.

    Args:
        media_id: ID of the media.
        user: Current authenticated user.
        db: Database session.

    Returns:
        List of history events for the media.

    Raises:
        HTTPException: If media not found.
    """
    # First verify media exists
    media = db.query(Media).filter(Media.id == media_id).first()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )

    # Get history for this media
    history_items = (
        db.query(History)
        .filter(History.media_id == media_id)
        .order_by(History.date.desc())
        .all()
    )

    return [history_to_response(h) for h in history_items]
