"""API key management routes for taggarr API."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.auth import generate_api_key, hash_api_key
from taggarr.db import ApiKey, User

router = APIRouter(prefix="/api/v1", tags=["apikeys"])


class CreateApiKeyRequest(BaseModel):
    """Request to create a new API key."""

    label: str = Field(..., min_length=1, max_length=255)


class ApiKeyResponse(BaseModel):
    """API key response (redacted)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    last_used_at: datetime | None


class CreateApiKeyResponse(BaseModel):
    """Response when creating API key (includes the key once)."""

    id: int
    label: str
    key: str  # Only returned on creation


@router.get("/apikey", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApiKey]:
    """List all API keys (keys are redacted).

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        List of API keys without the actual key values.
    """
    keys = db.query(ApiKey).all()
    return keys


@router.post(
    "/apikey", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    request: CreateApiKeyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreateApiKeyResponse:
    """Create a new API key. The key is only returned once.

    Args:
        request: Create API key request with label.
        user: Current authenticated user.
        db: Database session.

    Returns:
        Created API key with the raw key (shown only once).
    """
    # Generate the key
    raw_key = generate_api_key()
    hashed_key = hash_api_key(raw_key)

    # Store hashed key
    api_key = ApiKey(
        label=request.label,
        key=hashed_key,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Return the raw key (only time it's visible)
    return CreateApiKeyResponse(
        id=api_key.id,
        label=api_key.label,
        key=raw_key,
    )


@router.delete("/apikey/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete an API key.

    Args:
        key_id: ID of the API key to delete.
        user: Current authenticated user.
        db: Database session.

    Raises:
        HTTPException: If API key not found.
    """
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    db.delete(api_key)
    db.commit()
