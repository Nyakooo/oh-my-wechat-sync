#!/usr/bin/env python3
"""Read-only archive integrity and media health report."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

try:
    from archive_core.database import connect
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from archive_core.database import connect


def report(database: Path, archive_root: Path) -> dict[str, object]:
    connection = connect(database)
    try:
        foreign_key_errors = [dict(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()]
        referenced = {
            row[0]
            for row in connection.execute(
                "SELECT archive_path FROM attachments WHERE status = 'available' AND archive_path IS NOT NULL"
            )
        }
        media_root = archive_root / "media"
        files = [path for path in media_root.rglob("*") if path.is_file()] if media_root.is_dir() else []
        relative_files = {path.relative_to(archive_root).as_posix() for path in files}
        missing = sorted(referenced - relative_files)
        orphan = sorted(relative_files - referenced)
        return {
            "database": str(database),
            "archive_root": str(archive_root),
            "status": "ok" if not foreign_key_errors and not missing else "degraded",
            "counts": {
                "accounts": connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0],
                "messages": connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                "attachments": connection.execute("SELECT COUNT(*) FROM attachments").fetchone()[0],
                "media_files": len(files),
                "foreign_key_errors": len(foreign_key_errors),
                "missing_media": len(missing),
                "orphan_media": len(orphan),
            },
            "missing_media": missing,
            "orphan_media": orphan,
            "foreign_key_errors": foreign_key_errors,
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/archive.db"))
    parser.add_argument("--archive-root", type=Path, default=Path("data"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = report(args.database, args.archive_root)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
