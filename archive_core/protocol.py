from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from .models import SourceAttachment, SourceContact, SourceConversation, SourceMessage


@dataclass(frozen=True)
class SourceInfo:
    kind: str
    tool_name: str | None
    tool_version: str | None
    source_version: str | None


class ImportAdapter(Protocol):
    """Stable boundary between an external exporter and the archive core."""

    def detect(self) -> SourceInfo: ...

    def scan_contacts(self) -> Iterable[SourceContact]: ...

    def scan_conversations(self) -> Iterable[SourceConversation]: ...

    def scan_messages(self) -> Iterable[SourceMessage]: ...

    def scan_attachments(self) -> Iterable[SourceAttachment]: ...
