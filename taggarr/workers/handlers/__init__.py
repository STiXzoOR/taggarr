"""Command handlers for taggarr workers."""

from taggarr.workers.handlers.backup import BackupHandler
from taggarr.workers.handlers.scan import ScanHandler

# Command name to handler mapping
HANDLERS = {
    "ScanInstance": ScanHandler,
    "CreateBackup": BackupHandler,
}

__all__ = [
    "HANDLERS",
    "BackupHandler",
    "ScanHandler",
]
