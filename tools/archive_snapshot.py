#!/usr/bin/env python3
"""Create a consistent SQLite and media snapshot without changing the archive."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path

try:
    from archive_core.database import connect
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from archive_core.database import connect


def snapshot(database: Path, archive_root: Path, output: Path) -> dict[str, object]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"snapshot output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    target_database = output / "archive.db"
    source = connect(database)
    target = sqlite3.connect(target_database)
    try:
        source.backup(target)
        target.commit()
        media_source = archive_root / "media"
        media_target = output / "media"
        if media_source.is_dir():
            shutil.copytree(media_source, media_target, dirs_exist_ok=True)
        return {
            "database": str(target_database),
            "media_root": str(media_target),
            "media_files": sum(1 for path in media_target.rglob("*") if path.is_file()) if media_target.is_dir() else 0,
        }
    finally:
        target.close()
        source.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/archive.db"))
    parser.add_argument("--archive-root", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(snapshot(args.database, args.archive_root, args.output), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
