#!/usr/bin/env python3
"""Print a redacted, read-only summary for a valid import package."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from .validate_import_package import (
        ValidationError,
        load_json,
        load_ndjson,
        safe_relative_path,
        validate,
    )
except ImportError:  # pragma: no cover - used when invoked as a script
    from validate_import_package import (
        ValidationError,
        load_json,
        load_ndjson,
        safe_relative_path,
        validate,
    )


def build_report(package_root: Path) -> dict[str, Any]:
    counts = validate(package_root)
    manifest = load_json(package_root / "manifest.json")
    attachments = load_ndjson(package_root / "attachments.ndjson")
    media_kinds: Counter[str] = Counter()
    media_bytes = 0
    for index, attachment in enumerate(attachments, 1):
        media_kinds[str(attachment["kind"])] += 1
        media_path = safe_relative_path(attachment["path"], package_root, f"attachments.ndjson record {index}")
        media_bytes += media_path.stat().st_size

    source = manifest["source"]
    account = manifest["account"]
    return {
        "status": "valid",
        "format": manifest["format"],
        "format_version": manifest["format_version"],
        "created_at": manifest["created_at"],
        "source": {
            "kind": source.get("kind"),
            "tool_name": source.get("tool_name"),
            "tool_version": source.get("tool_version"),
            "wechat_version": source.get("wechat_version"),
        },
        "account": {
            "source_account_id_present": bool(account.get("source_account_id")),
            "display_name_present": bool(account.get("display_name")),
        },
        "records": counts,
        "media": {
            "attachment_count": len(attachments),
            "total_bytes": media_bytes,
            "kinds": dict(sorted(media_kinds.items())),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="path to a wechat-archive-import-v0 directory")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    args = parser.parse_args()
    try:
        report = build_report(args.package)
    except (ValidationError, OSError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    indent = 2 if args.pretty else None
    print(json.dumps(report, ensure_ascii=False, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
