"""Configuration routes for taggarr API."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from taggarr.api.deps import get_current_user, get_db
from taggarr.db import Config, User

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ConfigValue(BaseModel):
    """Config value request/response."""

    value: str


class ConfigResponse(BaseModel):
    """Config key-value response."""

    key: str
    value: str


class UIConfigResponse(BaseModel):
    """All UI-relevant configuration."""

    theme: str
    language: str
    page_size: int
    auto_refresh: bool


# UI config endpoint must be defined BEFORE the {key} route to avoid conflicts
@router.get("/ui", response_model=UIConfigResponse)
async def get_ui_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UIConfigResponse:
    """Get all UI-relevant configuration in one call.

    Args:
        user: Current authenticated user.
        db: Database session.

    Returns:
        All UI-relevant configuration values.
    """
    # Default values
    defaults = {
        "theme": "dark",
        "language": "en",
        "page_size": "25",
        "auto_refresh": "true",
    }

    result = {}
    for key, default in defaults.items():
        config = db.query(Config).filter(Config.key == f"ui.{key}").first()
        result[key] = config.value if config else default

    return UIConfigResponse(
        theme=result["theme"],
        language=result["language"],
        page_size=int(result["page_size"]),
        auto_refresh=result["auto_refresh"].lower() == "true",
    )


@router.get("/{key}", response_model=ConfigResponse)
async def get_config(
    key: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConfigResponse:
    """Get a configuration value by key.

    Args:
        key: The configuration key to retrieve.
        user: Current authenticated user.
        db: Database session.

    Returns:
        The configuration key-value pair.

    Raises:
        HTTPException: If the key is not found.
    """
    config = db.query(Config).filter(Config.key == key).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config key '{key}' not found",
        )

    return ConfigResponse(key=config.key, value=config.value)


@router.put("/{key}", response_model=ConfigResponse)
async def set_config(
    key: str,
    request: ConfigValue,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConfigResponse:
    """Set a configuration value (creates if not exists).

    Args:
        key: The configuration key to set.
        request: The configuration value.
        user: Current authenticated user.
        db: Database session.

    Returns:
        The updated configuration key-value pair.
    """
    config = db.query(Config).filter(Config.key == key).first()

    if config:
        config.value = request.value
    else:
        config = Config(key=key, value=request.value)
        db.add(config)

    db.commit()
    db.refresh(config)

    return ConfigResponse(key=config.key, value=config.value)
