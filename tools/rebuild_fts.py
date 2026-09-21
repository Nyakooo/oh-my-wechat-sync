#!/usr/bin/env python3
"""Rebuild the archive FTS index from canonical message rows."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

try:
    from archive_core.database import connect
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from archive_core.database import connect


def rebuild(connection: sqlite3.Connection) -> int:
    connection.execute("BEGIN")
    try:
        connection.execute("DELETE FROM messages_fts")
        connection.execute(
            """
            INSERT INTO messages_fts(message_id, account_id, conversation_id, content)
            SELECT id, account_id, conversation_id, content
            FROM messages
            WHERE content IS NOT NULL AND content <> ''
            """
        )
        count = connection.execute("SELECT COUNT(*) FROM messages_fts").fetchone()[0]
        connection.commit()
        return count
    except Exception:
        connection.rollback()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/archive.db"))
    args = parser.parse_args()
    with connect(args.database) as connection:
        print(rebuild(connection))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
