"""SQLite-backed, source-independent archive core."""

from .database import connect, initialize
from .importer import import_package, search_messages
from .migrations import CURRENT_SCHEMA_VERSION, migrate
from .protocol import ImportAdapter, SourceInfo
from .sync import SyncBusyError, SyncOrchestrator

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "ImportAdapter",
    "SourceInfo",
    "SyncBusyError",
    "SyncOrchestrator",
    "connect",
    "initialize",
    "import_package",
    "migrate",
    "search_messages",
]
