"""History routes for taggarr API."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.db import History, User

router = APIRouter(prefix="/api/v1", tags=["history"])


class HistoryListItem(BaseModel):
    """History item in list response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: datetime
    event_type: str
    media_id: int | None
    media_title: str | None
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


class PaginatedHistoryResponse(BaseModel):
    """Paginated list of history items."""

    items: list[HistoryListItem]
    total: int
    page: int
    page_size: int


def history_to_list_item(history: History) -> HistoryListItem:
    """Convert History model to list item response."""
    return HistoryListItem(
        id=history.id,
        date=history.date,
        event_type=history.event_type,
        media_id=history.media_id,
        media_title=history.media.title if history.media else None,
        instance_id=history.instance_id,
        data=history.data,
    )


@router.get("/history", response_model=PaginatedHistoryResponse)
async def list_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1),
    media_id: Optional[int] = Query(default=None),
    event: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedHistoryResponse:
    """List history events with pagination and filtering.

    Args:
        page: Page number (default 1).
        page_size: Number of items per page (default 25, max 100).
        media_id: Filter by media ID.
        event: Filter by event type.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Paginated list of history events.
    """
    # Cap page_size at 100
    page_size = min(page_size, 100)

    query = db.query(History)

    # Apply filters
    if media_id is not None:
        query = query.filter(History.media_id == media_id)
    if event:
        query = query.filter(History.event_type == event)

    # Get total count
    total = query.count()

    # Apply pagination with ordering by date descending
    offset = (page - 1) * page_size
    history_items = query.order_by(History.date.desc()).offset(offset).limit(page_size).all()

    return PaginatedHistoryResponse(
        items=[history_to_list_item(h) for h in history_items],
        total=total,
        page=page,
        page_size=page_size,
    )
