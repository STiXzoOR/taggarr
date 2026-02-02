"""Instance management routes for taggarr API."""

import json
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.db import Instance, User

router = APIRouter(prefix="/api/v1", tags=["instances"])


class InstanceCreate(BaseModel):
    """Request to create a new instance."""

    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(sonarr|radarr)$")
    url: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    root_path: str = Field(..., min_length=1)
    target_languages: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    target_genre: str | None = None
    quick_mode: bool = False
    enabled: bool = True
    require_original_default: bool = True
    notify_on_wrong_dub: bool = True
    notify_on_original_missing: bool = False


class InstanceUpdate(BaseModel):
    """Request to update an instance (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, pattern="^(sonarr|radarr)$")
    url: str | None = Field(default=None, min_length=1)
    api_key: str | None = Field(default=None, min_length=1)
    root_path: str | None = Field(default=None, min_length=1)
    target_languages: list[str] | None = None
    tags: list[str] | None = None
    target_genre: str | None = None
    quick_mode: bool | None = None
    enabled: bool | None = None
    require_original_default: bool | None = None
    notify_on_wrong_dub: bool | None = None
    notify_on_original_missing: bool | None = None


class InstanceResponse(BaseModel):
    """Instance response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    url: str
    api_key: str
    root_path: str
    target_languages: list[str]
    tags: list[str]
    target_genre: str | None
    quick_mode: bool
    enabled: bool
    require_original_default: bool
    notify_on_wrong_dub: bool
    notify_on_original_missing: bool

    @field_validator("target_languages", "tags", mode="before")
    @classmethod
    def parse_json_list(cls, v: str | list[str]) -> list[str]:
        """Parse JSON string to list if needed."""
        if isinstance(v, str):
            return json.loads(v)
        return v

    @field_validator("quick_mode", "enabled", "require_original_default",
                     "notify_on_wrong_dub", "notify_on_original_missing", mode="before")
    @classmethod
    def parse_int_bool(cls, v: int | bool) -> bool:
        """Parse integer to boolean if needed."""
        return bool(v)


class TestConnectionRequest(BaseModel):
    """Request to test connection to Sonarr/Radarr."""

    type: str = Field(..., pattern="^(sonarr|radarr)$")
    url: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)


class TestConnectionResponse(BaseModel):
    """Response for connection test."""

    success: bool
    message: str


def instance_to_response(instance: Instance) -> InstanceResponse:
    """Convert Instance model to response."""
    return InstanceResponse(
        id=instance.id,
        name=instance.name,
        type=instance.type,
        url=instance.url,
        api_key=instance.api_key,
        root_path=instance.root_path,
        target_languages=instance.target_languages,
        tags=instance.tags,
        target_genre=instance.target_genre,
        quick_mode=instance.quick_mode,
        enabled=instance.enabled,
        require_original_default=instance.require_original_default,
        notify_on_wrong_dub=instance.notify_on_wrong_dub,
        notify_on_original_missing=instance.notify_on_original_missing,
    )


# Test endpoint must be defined BEFORE /{id} routes to avoid conflicts
@router.post("/instance/test", response_model=TestConnectionResponse)
async def test_connection(
    request: TestConnectionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestConnectionResponse:
    """Test connection to Sonarr/Radarr instance.

    Args:
        request: Connection test request with type, URL, and API key.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Test result with success status and message.
    """
    # Validate URL format
    try:
        parsed = urlparse(request.url)
        if not parsed.scheme or not parsed.netloc:
            return TestConnectionResponse(
                success=False,
                message="Invalid URL format",
            )
    except Exception:
        return TestConnectionResponse(
            success=False,
            message="Invalid URL format",
        )

    # For now, just validate URL format and return mock success
    # Actual API testing will be added later
    return TestConnectionResponse(
        success=True,
        message=f"Connection to {request.type} validated (mock)",
    )


@router.get("/instance", response_model=list[InstanceResponse])
async def list_instances(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InstanceResponse]:
    """List all instances.

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        List of all instances.
    """
    instances = db.query(Instance).all()
    return [instance_to_response(inst) for inst in instances]


@router.get("/instance/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InstanceResponse:
    """Get instance by ID.

    Args:
        instance_id: ID of the instance to retrieve.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Instance details.

    Raises:
        HTTPException: If instance not found.
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )

    return instance_to_response(instance)


@router.post(
    "/instance", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED
)
async def create_instance(
    request: InstanceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InstanceResponse:
    """Create a new instance.

    Args:
        request: Instance creation request.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Created instance.

    Raises:
        HTTPException: If instance with same name already exists.
    """
    instance = Instance(
        name=request.name,
        type=request.type,
        url=request.url,
        api_key=request.api_key,
        root_path=request.root_path,
        target_languages=json.dumps(request.target_languages),
        tags=json.dumps(request.tags),
        target_genre=request.target_genre,
        quick_mode=1 if request.quick_mode else 0,
        enabled=1 if request.enabled else 0,
        require_original_default=1 if request.require_original_default else 0,
        notify_on_wrong_dub=1 if request.notify_on_wrong_dub else 0,
        notify_on_original_missing=1 if request.notify_on_original_missing else 0,
    )

    try:
        db.add(instance)
        db.commit()
        db.refresh(instance)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance with name '{request.name}' already exists",
        )

    return instance_to_response(instance)


@router.put("/instance/{instance_id}", response_model=InstanceResponse)
async def update_instance(
    instance_id: int,
    request: InstanceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InstanceResponse:
    """Update an instance.

    Args:
        instance_id: ID of the instance to update.
        request: Instance update request.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Updated instance.

    Raises:
        HTTPException: If instance not found.
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is None and field not in ("target_genre",):
            continue

        if field == "target_languages":
            setattr(instance, field, json.dumps(value))
        elif field == "tags":
            setattr(instance, field, json.dumps(value))
        elif field in ("quick_mode", "enabled", "require_original_default",
                       "notify_on_wrong_dub", "notify_on_original_missing"):
            setattr(instance, field, 1 if value else 0)
        else:
            setattr(instance, field, value)

    try:
        db.commit()
        db.refresh(instance)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance with name '{request.name}' already exists",
        )

    return instance_to_response(instance)


@router.delete("/instance/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete an instance.

    Args:
        instance_id: ID of the instance to delete.
        user: Current authenticated user.
        db: Database session.

    Raises:
        HTTPException: If instance not found.
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )

    db.delete(instance)
    db.commit()
