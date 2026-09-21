from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from archive_core.database import connect, initialize
from archive_core.importer import search_messages
from archive_core.queries import (
    account_summary,
    list_account_summaries,
    list_attachments,
    list_conversations,
    list_messages,
)


class AccountCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=200)
    wechat_id: str | None = Field(default=None, max_length=200)
    runtime_kind: str = Field(default="import", min_length=1, max_length=50)


class AccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    wechat_id: str | None = Field(default=None, max_length=200)


def _row(row: sqlite3.Row) -> dict[str, object]:
    return dict(row)


def _account_or_404(connection: sqlite3.Connection, account_id: str) -> sqlite3.Row:
    account = account_summary(connection, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    return account


def build_router(connection_factory, archive_root: Path | None = None):
    router = APIRouter(prefix="/api/v1")

    def db() -> Iterator[sqlite3.Connection]:
        with connection_factory() as connection:
            initialize(connection)
            yield connection

    @router.get("/accounts")
    def get_accounts(connection: sqlite3.Connection = Depends(db)) -> list[dict[str, object]]:
        return [_row(item) for item in list_account_summaries(connection)]

    @router.post("/accounts", status_code=201)
    def create_account(payload: AccountCreate, connection: sqlite3.Connection = Depends(db)) -> dict[str, object]:
        now = int(time.time() * 1000)
        try:
            connection.execute(
                """
                INSERT INTO accounts(id, display_name, wechat_id, runtime_kind, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (payload.id, payload.display_name, payload.wechat_id, payload.runtime_kind, now, now),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise HTTPException(status_code=409, detail="account already exists") from exc
        return _row(_account_or_404(connection, payload.id))

    @router.get("/accounts/{account_id}")
    def get_account(account_id: str, connection: sqlite3.Connection = Depends(db)) -> dict[str, object]:
        return _row(_account_or_404(connection, account_id))

    @router.patch("/accounts/{account_id}")
    def update_account(
        account_id: str,
        payload: AccountUpdate,
        connection: sqlite3.Connection = Depends(db),
    ) -> dict[str, object]:
        _account_or_404(connection, account_id)
        values = payload.model_dump(exclude_unset=True)
        if values:
            values["updated_at"] = int(time.time() * 1000)
            assignments = ", ".join(f"{key} = ?" for key in values)
            connection.execute(
                f"UPDATE accounts SET {assignments} WHERE id = ?",
                (*values.values(), account_id),
            )
            connection.commit()
        return _row(_account_or_404(connection, account_id))

    @router.delete("/accounts/{account_id}")
    def delete_account(
        account_id: str,
        confirm: bool = Query(default=False),
        connection: sqlite3.Connection = Depends(db),
    ) -> dict[str, object]:
        if not confirm:
            raise HTTPException(status_code=400, detail="account deletion requires confirm=true")
        _account_or_404(connection, account_id)
        running = connection.execute(
            "SELECT 1 FROM sync_jobs WHERE account_id = ? AND status = 'running' LIMIT 1",
            (account_id,),
        ).fetchone()
        if running is not None:
            raise HTTPException(status_code=409, detail="cannot delete an account with a running sync")
        try:
            connection.execute(
                "DELETE FROM messages_fts WHERE message_id IN (SELECT id FROM messages WHERE account_id = ?)",
                (account_id,),
            )
            connection.execute("DELETE FROM attachments WHERE account_id = ?", (account_id,))
            connection.execute("DELETE FROM messages WHERE account_id = ?", (account_id,))
            connection.execute(
                "DELETE FROM conversation_members WHERE conversation_id IN (SELECT id FROM conversations WHERE account_id = ?)",
                (account_id,),
            )
            connection.execute("DELETE FROM conversations WHERE account_id = ?", (account_id,))
            connection.execute("DELETE FROM contacts WHERE account_id = ?", (account_id,))
            connection.execute("DELETE FROM sync_checkpoints WHERE account_id = ?", (account_id,))
            connection.execute("DELETE FROM sync_jobs WHERE account_id = ?", (account_id,))
            connection.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return {"deleted": True, "account_id": account_id}

    @router.get("/accounts/{account_id}/conversations")
    def get_conversations(
        account_id: str,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        connection: sqlite3.Connection = Depends(db),
    ) -> list[dict[str, object]]:
        _account_or_404(connection, account_id)
        return [_row(item) for item in list_conversations(connection, account_id, limit, offset)]

    @router.get("/accounts/{account_id}/conversations/{conversation_id}/messages")
    def get_messages(
        account_id: str,
        conversation_id: str,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        connection: sqlite3.Connection = Depends(db),
    ) -> list[dict[str, object]]:
        _account_or_404(connection, account_id)
        conversation = connection.execute(
            "SELECT id FROM conversations WHERE id = ? AND account_id = ?",
            (conversation_id, account_id),
        ).fetchone()
        if conversation is None:
            raise HTTPException(status_code=404, detail="conversation not found")
        messages = []
        for item in list_messages(connection, account_id, conversation_id, limit, offset):
            result = _row(item)
            result["attachments"] = [_row(attachment) for attachment in list_attachments(connection, item["id"])]
            messages.append(result)
        return messages

    @router.get("/accounts/{account_id}/attachments/{attachment_id}")
    def get_attachment(
        account_id: str,
        attachment_id: str,
        connection: sqlite3.Connection = Depends(db),
    ) -> dict[str, object]:
        _account_or_404(connection, account_id)
        attachment = connection.execute(
            "SELECT * FROM attachments WHERE id = ? AND account_id = ?",
            (attachment_id, account_id),
        ).fetchone()
        if attachment is None:
            raise HTTPException(status_code=404, detail="attachment not found")
        return _row(attachment)

    @router.get("/accounts/{account_id}/attachments/{attachment_id}/content")
    def get_attachment_content(
        account_id: str,
        attachment_id: str,
        connection: sqlite3.Connection = Depends(db),
    ):
        if archive_root is None:
            raise HTTPException(status_code=503, detail="archive media storage is not configured")
        _account_or_404(connection, account_id)
        attachment = connection.execute(
            "SELECT archive_path, mime_type, original_name, status FROM attachments WHERE id = ? AND account_id = ?",
            (attachment_id, account_id),
        ).fetchone()
        if attachment is None:
            raise HTTPException(status_code=404, detail="attachment not found")
        if attachment["status"] != "available" or not attachment["archive_path"]:
            raise HTTPException(status_code=404, detail="attachment content is unavailable")
        root = archive_root.resolve()
        media_path = (root / attachment["archive_path"]).resolve()
        if root not in media_path.parents or not media_path.is_file():
            raise HTTPException(status_code=404, detail="attachment content is unavailable")
        return FileResponse(
            media_path,
            media_type=attachment["mime_type"] or "application/octet-stream",
            filename=attachment["original_name"] or media_path.name,
        )

    @router.get("/search")
    def search(
        account_id: str,
        q: str = Query(min_length=1, max_length=200),
        limit: int = Query(default=50, ge=1, le=200),
        connection: sqlite3.Connection = Depends(db),
    ) -> list[dict[str, object]]:
        _account_or_404(connection, account_id)
        return [_row(item) for item in search_messages(connection, account_id, q, limit)]

    @router.get("/sync/jobs/{job_id}")
    def get_sync_job(job_id: str, connection: sqlite3.Connection = Depends(db)) -> dict[str, object]:
        job = connection.execute("SELECT * FROM sync_jobs WHERE id = ?", (job_id,)).fetchone()
        if job is None:
            raise HTTPException(status_code=404, detail="sync job not found")
        return _row(job)

    return router


def default_paths() -> tuple[Path, Path]:
    return (
        Path(os.environ.get("WECHAT_ARCHIVE_DB", "data/archive.db")),
        Path(os.environ.get("WECHAT_ARCHIVE_ROOT", "data")),
    )


def connection_factory_for(database_path: Path):
    def factory() -> sqlite3.Connection:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        return connect(database_path)

    return factory
