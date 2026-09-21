"""SQLite-backed, source-independent archive core."""

from .database import connect, initialize
from .importer import import_package, search_messages
from .migrations import CURRENT_SCHEMA_VERSION, migrate
from .protocol import ImportAdapter, SourceInfo
from .runtime import RuntimeAdapter, RuntimeManager, RuntimeStatus, RuntimeUnavailableError
from .sync import SyncBusyError, SyncCancelledError, SyncOrchestrator

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "ImportAdapter",
    "SourceInfo",
    "RuntimeAdapter",
    "RuntimeManager",
    "RuntimeStatus",
    "RuntimeUnavailableError",
    "SyncBusyError",
    "SyncCancelledError",
    "SyncOrchestrator",
    "connect",
    "initialize",
    "import_package",
    "migrate",
    "search_messages",
]
