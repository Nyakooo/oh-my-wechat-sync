from __future__ import annotations

import sqlite3
from pathlib import Path


CURRENT_SCHEMA_VERSION = 1
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def migrate(connection: sqlite3.Connection) -> int:
    """Apply the current schema and return the schema version."""
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    row = connection.execute("SELECT value FROM archive_meta WHERE key = 'schema_version'").fetchone()
    if row is None:
        connection.execute(
            "INSERT INTO archive_meta(key, value) VALUES ('schema_version', ?)",
            (str(CURRENT_SCHEMA_VERSION),),
        )
        connection.commit()
        return CURRENT_SCHEMA_VERSION
    version = int(row[0])
    if version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(f"database schema {version} is newer than supported {CURRENT_SCHEMA_VERSION}")
    if version < CURRENT_SCHEMA_VERSION:
        connection.execute(
            "UPDATE archive_meta SET value = ? WHERE key = 'schema_version'",
            (str(CURRENT_SCHEMA_VERSION),),
        )
        connection.commit()
    return CURRENT_SCHEMA_VERSION
