"""API routes for taggarr."""

from taggarr.api.routes.apikeys import router as apikeys_router
from taggarr.api.routes.auth import router as auth_router
from taggarr.api.routes.backups import router as backups_router
from taggarr.api.routes.commands import router as commands_router
from taggarr.api.routes.config import router as config_router
from taggarr.api.routes.history import router as history_router
from taggarr.api.routes.instances import router as instances_router
from taggarr.api.routes.logs import router as logs_router
from taggarr.api.routes.media import router as media_router
from taggarr.api.routes.notifications import router as notifications_router
from taggarr.api.routes.stats import router as stats_router
from taggarr.api.routes.tags import router as tags_router

__all__ = [
    "auth_router",
    "apikeys_router",
    "backups_router",
    "commands_router",
    "config_router",
    "history_router",
    "instances_router",
    "logs_router",
    "media_router",
    "notifications_router",
    "stats_router",
    "tags_router",
]
