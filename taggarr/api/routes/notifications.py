"""Notification management routes for taggarr API."""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.db import Notification, User
from taggarr.workers.providers import get_provider

router = APIRouter(prefix="/api/v1", tags=["notifications"])

# Available notification providers
NOTIFICATION_PROVIDERS = [
    {"id": "discord", "name": "Discord", "config_fields": ["webhook_url"]},
    {"id": "telegram", "name": "Telegram", "config_fields": ["bot_token", "chat_id"]},
    {"id": "pushover", "name": "Pushover", "config_fields": ["user_key", "api_token"]},
    {
        "id": "email",
        "name": "Email",
        "config_fields": [
            "smtp_server",
            "smtp_port",
            "username",
            "password",
            "from_address",
            "to_address",
        ],
    },
    {"id": "webhook", "name": "Webhook", "config_fields": ["url", "method"]},
]


class NotificationCreate(BaseModel):
    """Request to create a new notification."""

    name: str = Field(..., min_length=1, max_length=255)
    implementation: str = Field(..., min_length=1)
    settings: dict = Field(default_factory=dict)
    on_scan_completed: bool = False
    on_wrong_dub_detected: bool = True
    on_original_missing: bool = True
    on_health_issue: bool = False
    on_application_update: bool = False
    include_health_warnings: bool = False
    tags: list[str] | None = None


class NotificationUpdate(BaseModel):
    """Request to update a notification (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    implementation: str | None = Field(default=None, min_length=1)
    settings: dict | None = None
    on_scan_completed: bool | None = None
    on_wrong_dub_detected: bool | None = None
    on_original_missing: bool | None = None
    on_health_issue: bool | None = None
    on_application_update: bool | None = None
    include_health_warnings: bool | None = None
    tags: list[str] | None = None


class NotificationResponse(BaseModel):
    """Notification response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    implementation: str
    settings: dict
    on_scan_completed: bool
    on_wrong_dub_detected: bool
    on_original_missing: bool
    on_health_issue: bool
    on_application_update: bool
    include_health_warnings: bool
    tags: list[str] | None

    @field_validator("settings", mode="before")
    @classmethod
    def parse_settings_json(cls, v: str | dict) -> dict:
        """Parse JSON string to dict if needed."""
        if isinstance(v, str):
            return json.loads(v)
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags_json(cls, v: str | list | None) -> list[str] | None:
        """Parse JSON string to list if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            return json.loads(v)
        return v

    @field_validator(
        "on_scan_completed",
        "on_wrong_dub_detected",
        "on_original_missing",
        "on_health_issue",
        "on_application_update",
        "include_health_warnings",
        mode="before",
    )
    @classmethod
    def parse_int_bool(cls, v: int | bool) -> bool:
        """Parse integer to boolean if needed."""
        return bool(v)


class TestNotificationRequest(BaseModel):
    """Request to test a notification configuration."""

    implementation: str = Field(..., min_length=1)
    settings: dict = Field(default_factory=dict)


class TestNotificationResponse(BaseModel):
    """Response for notification test."""

    success: bool
    message: str


class NotificationProviderSchema(BaseModel):
    """Notification provider schema."""

    id: str
    name: str
    config_fields: list[str]


def notification_to_response(notification: Notification) -> NotificationResponse:
    """Convert Notification model to response."""
    return NotificationResponse(
        id=notification.id,
        name=notification.name,
        implementation=notification.implementation,
        settings=notification.settings,
        on_scan_completed=notification.on_scan_completed,
        on_wrong_dub_detected=notification.on_wrong_dub_detected,
        on_original_missing=notification.on_original_missing,
        on_health_issue=notification.on_health_issue,
        on_application_update=notification.on_application_update,
        include_health_warnings=notification.include_health_warnings,
        tags=notification.tags,
    )


# Test and schema endpoints must be defined BEFORE /{id} routes to avoid conflicts
@router.post("/notification/test", response_model=TestNotificationResponse)
async def test_notification(
    request: TestNotificationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestNotificationResponse:
    """Test a notification configuration.

    Args:
        request: Notification test request with implementation and settings.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Test result with success status and message.
    """
    # Validate that the implementation is known
    known_implementations = {p["id"] for p in NOTIFICATION_PROVIDERS}
    if request.implementation not in known_implementations:
        return TestNotificationResponse(
            success=False,
            message=f"Unknown implementation: {request.implementation}",
        )

    try:
        provider_class = get_provider(request.implementation)
        provider = provider_class()
        success, message = await provider.test(request.settings)
        return TestNotificationResponse(success=success, message=message)
    except ValueError as e:
        return TestNotificationResponse(
            success=False,
            message=str(e),
        )
    except Exception as e:
        return TestNotificationResponse(
            success=False,
            message=f"Test failed: {e}",
        )


@router.get("/notification/schema", response_model=list[NotificationProviderSchema])
async def get_notification_schema(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get list of available notification providers.

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        List of available notification providers with config fields.
    """
    return NOTIFICATION_PROVIDERS


@router.get("/notification", response_model=list[NotificationResponse])
async def list_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    """List all notifications.

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        List of all notifications.
    """
    notifications = db.query(Notification).all()
    return [notification_to_response(n) for n in notifications]


@router.get("/notification/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """Get notification by ID.

    Args:
        notification_id: ID of the notification to retrieve.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Notification details.

    Raises:
        HTTPException: If notification not found.
    """
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return notification_to_response(notification)


@router.post(
    "/notification",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification(
    request: NotificationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """Create a new notification.

    Args:
        request: Notification creation request.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Created notification.

    Raises:
        HTTPException: If notification with same name already exists.
    """
    # Check for duplicate name
    existing = db.query(Notification).filter(Notification.name == request.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Notification with name '{request.name}' already exists",
        )

    notification = Notification(
        name=request.name,
        implementation=request.implementation,
        settings=json.dumps(request.settings),
        on_scan_completed=1 if request.on_scan_completed else 0,
        on_wrong_dub_detected=1 if request.on_wrong_dub_detected else 0,
        on_original_missing=1 if request.on_original_missing else 0,
        on_health_issue=1 if request.on_health_issue else 0,
        on_application_update=1 if request.on_application_update else 0,
        include_health_warnings=1 if request.include_health_warnings else 0,
        tags=json.dumps(request.tags) if request.tags else None,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification_to_response(notification)


@router.put("/notification/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: int,
    request: NotificationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """Update a notification.

    Args:
        notification_id: ID of the notification to update.
        request: Notification update request.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Updated notification.

    Raises:
        HTTPException: If notification not found.
    """
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)

    # Check for duplicate name if name is being updated
    if "name" in update_data and update_data["name"] != notification.name:
        existing = (
            db.query(Notification)
            .filter(Notification.name == update_data["name"])
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Notification name already exists",
            )

    for field, value in update_data.items():
        if value is None and field not in ("tags",):
            continue

        if field == "settings":
            setattr(notification, field, json.dumps(value))
        elif field == "tags":
            setattr(notification, field, json.dumps(value) if value else None)
        elif field in (
            "on_scan_completed",
            "on_wrong_dub_detected",
            "on_original_missing",
            "on_health_issue",
            "on_application_update",
            "include_health_warnings",
        ):
            setattr(notification, field, 1 if value else 0)
        else:
            setattr(notification, field, value)

    db.commit()
    db.refresh(notification)

    return notification_to_response(notification)


@router.delete("/notification/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a notification.

    Args:
        notification_id: ID of the notification to delete.
        user: Current authenticated user.
        db: Database session.

    Raises:
        HTTPException: If notification not found.
    """
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    db.delete(notification)
    db.commit()
