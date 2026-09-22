#!/usr/bin/env python3
"""Seed a clearly synthetic demo account into an empty account slot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

try:
    from archive_core.database import connect, initialize
    from archive_core.importer import import_package
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from archive_core.database import connect, initialize
    from archive_core.importer import import_package


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def _write_ndjson(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_demo_package(root: Path) -> Path:
    package = root / "synthetic-demo"
    media = package / "media"
    media.mkdir(parents=True)
    contacts = [
        {"source_contact_id": "demo-self", "display_name": "我（虚构）", "alias": "demo-self"},
        {"source_contact_id": "demo-lin", "display_name": "林同学（虚构）", "alias": "demo-lin"},
        {"source_contact_id": "demo-zhou", "display_name": "周同学（虚构）", "alias": "demo-zhou"},
    ]
    conversations = [
        {"source_chat_id": "demo-direct", "kind": "direct", "title": "林同学（虚构）", "member_source_ids": ["demo-self", "demo-lin"]},
        {"source_chat_id": "demo-group", "kind": "group", "title": "周末计划（虚构群）", "member_source_ids": ["demo-self", "demo-lin", "demo-zhou"]},
    ]
    base = 1_727_000_000_000
    messages = [
        {"source_msg_id": "demo-msg-01", "source_chat_id": "demo-direct", "sender_source_contact_id": "demo-lin", "source_created_at": base, "type": "text", "content": "演示数据：周末想去公园走走吗？ weekend park plan", "is_self": False},
        {"source_msg_id": "demo-msg-02", "source_chat_id": "demo-direct", "sender_source_contact_id": "demo-self", "source_created_at": base + 60_000, "type": "text", "content": "好呀，我可以带上相机。", "is_self": True, "reply_to_source_msg_id": "demo-msg-01"},
        {"source_msg_id": "demo-msg-03", "source_chat_id": "demo-group", "sender_source_contact_id": "demo-zhou", "source_created_at": base + 3_600_000, "type": "text", "content": "虚构群聊：周六上午十点集合，地点之后再定。", "is_self": False},
        {"source_msg_id": "demo-msg-04", "source_chat_id": "demo-group", "sender_source_contact_id": "demo-lin", "source_created_at": base + 3_660_000, "type": "text", "content": "我来整理路线，大家可以搜索‘集合’查看这条消息。", "is_self": False},
        {"source_msg_id": "demo-msg-05", "source_chat_id": "demo-direct", "sender_source_contact_id": "demo-lin", "source_created_at": base + 86_400_000, "type": "image", "content": "一张人工绘制的虚构示意图", "is_self": False},
        {"source_msg_id": "demo-msg-06", "source_chat_id": "demo-group", "sender_source_contact_id": "demo-self", "source_created_at": base + 90_000_000, "type": "file", "content": "演示行程清单已整理。", "is_self": True},
    ]
    svg_path = media / "demo-sketch.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
        '<rect width="640" height="360" rx="28" fill="#e5f2ea"/>'
        '<path d="M0 270 Q150 170 300 255 T640 210 V360 H0Z" fill="#a6ceb2"/>'
        '<circle cx="490" cy="92" r="40" fill="#f5d98d"/>'
        '<text x="42" y="72" font-family="sans-serif" font-size="24" fill="#335747">SYNTHETIC DEMO ART</text>'
        '<text x="42" y="112" font-family="sans-serif" font-size="15" fill="#5d7669">No real people or chat data</text>'
        '</svg>',
        encoding="utf-8",
    )
    text_path = media / "demo-itinerary.txt"
    text_path.write_text("Fictional demo itinerary\n10:00 meet at the park entrance\n", encoding="utf-8")
    attachments = [
        {"source_msg_id": "demo-msg-05", "kind": "image", "mime_type": "image/svg+xml", "original_name": "synthetic-park-sketch.svg", "size": svg_path.stat().st_size, "sha256": _sha256(svg_path), "path": f"media/{svg_path.name}"},
        {"source_msg_id": "demo-msg-06", "kind": "file", "mime_type": "text/plain", "original_name": "synthetic-itinerary.txt", "size": text_path.stat().st_size, "sha256": _sha256(text_path), "path": f"media/{text_path.name}"},
    ]
    members = [
        {"source_chat_id": "demo-direct", "source_contact_id": contact_id}
        for contact_id in ("demo-self", "demo-lin")
    ] + [
        {"source_chat_id": "demo-group", "source_contact_id": contact_id}
        for contact_id in ("demo-self", "demo-lin", "demo-zhou")
    ]
    records = {
        "contacts.ndjson": contacts,
        "conversations.ndjson": conversations,
        "conversation-members.ndjson": members,
        "messages.ndjson": messages,
        "attachments.ndjson": attachments,
    }
    files = {}
    for name, values in records.items():
        path = package / name
        _write_ndjson(path, values)
        files[name] = {"records": len(values), "sha256": _sha256(path)}
    _write_json(
        package / "manifest.json",
        {
            "format": "wechat-archive-import",
            "format_version": 0,
            "export_id": "synthetic-demo-export-v1",
            "source": {"kind": "offline-tool", "tool_name": "seed-demo", "tool_version": "1", "wechat_version": "synthetic"},
            "account": {"source_account_id": "synthetic-demo-account", "display_name": "演示微信（全为虚构数据）"},
            "files": files,
            "created_at": "2026-09-22T00:00:00Z",
        },
    )
    return package


def seed(database: Path, archive_root: Path, account_id: str) -> dict[str, int]:
    connection = connect(database)
    try:
        initialize(connection)
        if connection.execute("SELECT 1 FROM accounts WHERE id = ?", (account_id,)).fetchone():
            raise ValueError(f"account already exists: {account_id}; demo seeding will not overwrite it")
        with tempfile.TemporaryDirectory(prefix="wechat-archive-demo-") as temporary:
            package = create_demo_package(Path(temporary))
            return import_package(connection, package, archive_root, account_id, "演示微信（全为虚构数据）")
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/archive.db"))
    parser.add_argument("--archive-root", type=Path, default=Path("data"))
    parser.add_argument("--account-id", default="demo-account")
    args = parser.parse_args()
    try:
        stats = seed(args.database, args.archive_root, args.account_id)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"account_id": args.account_id, "synthetic_only": True, "stats": stats}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
