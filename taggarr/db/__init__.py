"""Database package for taggarr."""

from taggarr.db.database import create_engine, get_session
from taggarr.db.migrations import init_db
from taggarr.db.models import (
    ApiKey,
    Backup,
    Base,
    Command,
    Config,
    History,
    Instance,
    Media,
    Notification,
    NotificationStatus,
    ScheduledTask,
    Season,
    SessionModel,
    Tag,
    User,
)

__all__ = [
    "create_engine",
    "get_session",
    "init_db",
    "Base",
    "User",
    "SessionModel",
    "ApiKey",
    "Config",
    "Instance",
    "Tag",
    "Media",
    "Season",
    "History",
    "Notification",
    "NotificationStatus",
    "Command",
    "ScheduledTask",
    "Backup",
]
