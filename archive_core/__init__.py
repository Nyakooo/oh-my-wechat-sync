"""SQLite-backed, source-independent archive core."""

from .database import connect, initialize
from .importer import import_package, search_messages

__all__ = ["connect", "initialize", "import_package", "search_messages"]
