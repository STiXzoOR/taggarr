"""API routes for taggarr."""

from taggarr.api.routes.apikeys import router as apikeys_router
from taggarr.api.routes.auth import router as auth_router
from taggarr.api.routes.config import router as config_router

__all__ = ["auth_router", "apikeys_router", "config_router"]
