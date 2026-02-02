"""API routes for taggarr."""

from taggarr.api.routes.apikeys import router as apikeys_router
from taggarr.api.routes.auth import router as auth_router
from taggarr.api.routes.config import router as config_router
from taggarr.api.routes.instances import router as instances_router
from taggarr.api.routes.media import router as media_router
from taggarr.api.routes.tags import router as tags_router

__all__ = ["auth_router", "apikeys_router", "config_router", "instances_router", "media_router", "tags_router"]
