from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceContact:
    source_contact_id: str
    display_name: str | None
    alias: str | None


@dataclass(frozen=True)
class SourceConversation:
    source_chat_id: str
    kind: str
    title: str | None
    member_source_ids: tuple[str, ...]


@dataclass(frozen=True)
class SourceMessage:
    source_msg_id: str
    source_chat_id: str
    sender_source_contact_id: str | None
    source_created_at: int
    message_type: str
    content: str | None
    is_self: bool
    reply_to_source_msg_id: str | None


@dataclass(frozen=True)
class SourceAttachment:
    source_msg_id: str
    kind: str
    mime_type: str | None
    original_name: str | None
    size: int | None
    sha256: str
    path: str
