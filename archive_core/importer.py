from __future__ import annotations

import hashlib
import shutil
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any

from tools.validate_import_package import load_json, load_ndjson, safe_relative_path, validate

from .models import SourceAttachment, SourceContact, SourceConversation, SourceMessage


def _now_ms() -> int:
    return int(time.time() * 1000)


def _stable_id(prefix: str, account_id: str, source_id: str) -> str:
    digest = hashlib.sha256(f"{account_id}\0{source_id}".encode("utf-8")).hexdigest()[:32]
    return f"{prefix}_{digest}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_models(package_root: Path) -> tuple[list[SourceContact], list[SourceConversation], list[SourceMessage], list[SourceAttachment], list[dict[str, Any]]]:
    contacts = [
        SourceContact(record["source_contact_id"], record.get("display_name"), record.get("alias"))
        for record in load_ndjson(package_root / "contacts.ndjson")
    ]
    conversations = [
        SourceConversation(
            record["source_chat_id"],
            record["kind"],
            record.get("title"),
            tuple(record.get("member_source_ids", [])),
        )
        for record in load_ndjson(package_root / "conversations.ndjson")
    ]
    messages = [
        SourceMessage(
            record["source_msg_id"],
            record["source_chat_id"],
            record.get("sender_source_contact_id"),
            record["source_created_at"],
            record["type"],
            record.get("content"),
            bool(record.get("is_self", False)),
            record.get("reply_to_source_msg_id"),
        )
        for record in load_ndjson(package_root / "messages.ndjson")
    ]
    attachments = [
        SourceAttachment(
            record["source_msg_id"],
            record["kind"],
            record.get("mime_type"),
            record.get("original_name"),
            record.get("size"),
            record["sha256"],
            record["path"],
        )
        for record in load_ndjson(package_root / "attachments.ndjson")
    ]
    members = load_ndjson(package_root / "conversation-members.ndjson") if (package_root / "conversation-members.ndjson").is_file() else []
    return contacts, conversations, messages, attachments, members


def import_package(
    connection: sqlite3.Connection,
    package_root: str | Path,
    archive_root: str | Path,
    account_id: str,
    display_name: str | None = None,
    now_ms: int | None = None,
) -> dict[str, int]:
    package = Path(package_root).resolve()
    archive = Path(archive_root).resolve()
    if not account_id:
        raise ValueError("account_id is required")
    validate(package)
    manifest = load_json(package / "manifest.json")
    contacts, conversations, messages, attachments, members = _source_models(package)
    timestamp = now_ms if now_ms is not None else _now_ms()
    archive.mkdir(parents=True, exist_ok=True)
    media_root = archive / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    created_media: list[Path] = []
    stats = Counter()
    contact_ids = {item.source_contact_id: _stable_id("contact", account_id, item.source_contact_id) for item in contacts}
    conversation_ids = {item.source_chat_id: _stable_id("conversation", account_id, item.source_chat_id) for item in conversations}
    message_ids = {item.source_msg_id: _stable_id("message", account_id, item.source_msg_id) for item in messages}

    try:
        connection.execute("BEGIN")
        connection.execute(
            """INSERT INTO accounts(id, display_name, runtime_kind, runtime_ref, status, created_at, updated_at)
               VALUES (?, ?, 'import', ?, 'ready', ?, ?)
               ON CONFLICT(id) DO UPDATE SET display_name = excluded.display_name, updated_at = excluded.updated_at, status = 'ready'""",
            (account_id, display_name or manifest["account"].get("display_name") or account_id, manifest["source"].get("tool_name"), timestamp, timestamp),
        )

        for contact in contacts:
            connection.execute(
                """INSERT INTO contacts(id, account_id, source_contact_id, display_name, alias)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(account_id, source_contact_id) DO UPDATE SET display_name = excluded.display_name, alias = excluded.alias""",
                (contact_ids[contact.source_contact_id], account_id, contact.source_contact_id, contact.display_name, contact.alias),
            )
            stats["contacts_seen"] += 1

        for conversation in conversations:
            connection.execute(
                """INSERT INTO conversations(id, account_id, source_chat_id, kind, title)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(account_id, source_chat_id) DO UPDATE SET kind = excluded.kind, title = excluded.title""",
                (conversation_ids[conversation.source_chat_id], account_id, conversation.source_chat_id, conversation.kind, conversation.title),
            )
            stats["conversations_seen"] += 1
            for source_contact_id in conversation.member_source_ids:
                connection.execute(
                    "INSERT OR IGNORE INTO conversation_members(conversation_id, contact_id) VALUES (?, ?)",
                    (conversation_ids[conversation.source_chat_id], contact_ids[source_contact_id]),
                )

        for member in members:
            connection.execute(
                "INSERT OR IGNORE INTO conversation_members(conversation_id, contact_id) VALUES (?, ?)",
                (conversation_ids[member["source_chat_id"]], contact_ids[member["source_contact_id"]]),
            )

        for message in messages:
            message_id = message_ids[message.source_msg_id]
            existing = connection.execute("SELECT 1 FROM messages WHERE account_id = ? AND source_msg_id = ?", (account_id, message.source_msg_id)).fetchone()
            connection.execute(
                """INSERT INTO messages(id, account_id, conversation_id, sender_contact_id, source_msg_id, source_created_at, type, content, is_self, archived_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(account_id, source_msg_id) DO UPDATE SET conversation_id = excluded.conversation_id,
                     sender_contact_id = excluded.sender_contact_id, source_created_at = excluded.source_created_at,
                     type = excluded.type, content = excluded.content, is_self = excluded.is_self, archived_at = excluded.archived_at""",
                (
                    message_id,
                    account_id,
                    conversation_ids[message.source_chat_id],
                    contact_ids.get(message.sender_source_contact_id),
                    message.source_msg_id,
                    message.source_created_at,
                    message.message_type,
                    message.content,
                    int(message.is_self),
                    timestamp,
                ),
            )
            connection.execute("DELETE FROM messages_fts WHERE message_id = ?", (message_id,))
            if message.content:
                connection.execute("INSERT INTO messages_fts(message_id, account_id, conversation_id, content) VALUES (?, ?, ?, ?)", (message_id, account_id, conversation_ids[message.source_chat_id], message.content))
            stats["messages_updated" if existing else "messages_inserted"] += 1

        for message in messages:
            if message.reply_to_source_msg_id:
                connection.execute("UPDATE messages SET reply_to_id = ? WHERE id = ?", (message_ids.get(message.reply_to_source_msg_id), message_ids[message.source_msg_id]))

        for attachment in attachments:
            source_path = safe_relative_path(attachment.path, package, "attachment")
            destination = media_root / attachment.sha256
            if destination.exists():
                if _sha256(destination) != attachment.sha256:
                    raise ValueError(f"archive media hash collision: {attachment.sha256}")
                stats["media_reused"] += 1
            else:
                shutil.copyfile(source_path, destination)
                created_media.append(destination)
                stats["media_created"] += 1
            attachment_id = _stable_id("attachment", account_id, f"{message_ids[attachment.source_msg_id]}:{attachment.kind}:{attachment.sha256}")
            existing = connection.execute("SELECT 1 FROM attachments WHERE account_id = ? AND message_id = ? AND kind = ? AND sha256 = ?", (account_id, message_ids[attachment.source_msg_id], attachment.kind, attachment.sha256)).fetchone()
            connection.execute(
                """INSERT INTO attachments(id, account_id, message_id, kind, mime_type, original_name, size, source_path, archive_path, sha256, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')
                   ON CONFLICT(account_id, message_id, kind, sha256) DO UPDATE SET mime_type = excluded.mime_type,
                     original_name = excluded.original_name, size = excluded.size, source_path = excluded.source_path,
                     archive_path = excluded.archive_path, status = 'available'""",
                (attachment_id, account_id, message_ids[attachment.source_msg_id], attachment.kind, attachment.mime_type, attachment.original_name, attachment.size, attachment.path, f"media/{attachment.sha256}", attachment.sha256),
            )
            stats["attachments_updated" if existing else "attachments_inserted"] += 1

        connection.execute("UPDATE accounts SET last_sync_at = ?, updated_at = ? WHERE id = ?", (timestamp, timestamp, account_id))
        connection.commit()
    except Exception:
        connection.rollback()
        for media_path in created_media:
            media_path.unlink(missing_ok=True)
        raise
    for key in (
        "contacts_seen",
        "conversations_seen",
        "messages_inserted",
        "messages_updated",
        "attachments_inserted",
        "attachments_updated",
        "media_created",
        "media_reused",
    ):
        stats.setdefault(key, 0)
    return dict(stats)


def search_messages(connection: sqlite3.Connection, account_id: str, query: str, limit: int = 50) -> list[sqlite3.Row]:
    if not query.strip():
        return []
    return connection.execute(
        """SELECT messages.id, messages.source_msg_id, messages.content, messages.source_created_at,
                  messages.conversation_id
           FROM messages_fts
           JOIN messages ON messages.id = messages_fts.message_id
           WHERE messages_fts MATCH ? AND messages.account_id = ?
           ORDER BY messages.source_created_at
           LIMIT ?""",
        (query, account_id, limit),
    ).fetchall()
