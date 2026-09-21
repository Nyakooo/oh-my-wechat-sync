#!/usr/bin/env python3
"""Import a validated offline package into a local SQLite archive."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from archive_core import connect, import_package, initialize
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from archive_core import connect, import_package, initialize


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="path to a validated import package")
    parser.add_argument("--db", type=Path, required=True, help="SQLite archive database path")
    parser.add_argument("--data", type=Path, required=True, help="archive data directory for media")
    parser.add_argument("--account-id", required=True, help="Archive-local account identifier")
    parser.add_argument("--display-name", help="optional archive display name")
    args = parser.parse_args()

    connection = connect(args.db)
    try:
        initialize(connection)
        stats = import_package(connection, args.package, args.data, args.account_id, args.display_name)
    except Exception as exc:
        connection.close()
        print(f"IMPORT_FAILED: {exc}", file=sys.stderr)
        return 1
    connection.close()
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
