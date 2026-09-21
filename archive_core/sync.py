from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from tools.validate_import_package import load_json

from .importer import import_package


class SyncBusyError(RuntimeError):
    """Raised when another import sync is already running in this process."""


class SyncCancelledError(RuntimeError):
    """Raised when an Import-first job is cancelled before its import starts."""


class SyncOrchestrator:
    """Import-first sync orchestration with jobs and checkpoints."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._lock = threading.Lock()

    def sync_package(
        self,
        package_root: str | Path,
        archive_root: str | Path,
        account_id: str,
        display_name: str | None = None,
        source_name: str = "offline-import",
        job_id: str | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, object]:
        if not self._lock.acquire(blocking=False):
            raise SyncBusyError("another sync is already running")
        job_id = job_id or f"job_{uuid.uuid4().hex}"
        cancel_event = cancel_event or threading.Event()
        started_at = int(time.time() * 1000)
        try:
            try:
                self.connection.execute(
                    "INSERT INTO sync_locks(lock_name, job_id, acquired_at) VALUES ('global', ?, ?)",
                    (job_id, started_at),
                )
                self.connection.commit()
            except sqlite3.IntegrityError as exc:
                self.connection.rollback()
                raise SyncBusyError("another sync is already recorded in the archive") from exc
            self.connection.execute(
                """INSERT INTO accounts(id, display_name, runtime_kind, status, created_at, updated_at)
                   VALUES (?, ?, 'import', 'syncing', ?, ?)
                   ON CONFLICT(id) DO UPDATE SET status = 'syncing', updated_at = excluded.updated_at""",
                (account_id, display_name or account_id, started_at, started_at),
            )
            self.connection.execute(
                """INSERT INTO sync_jobs(id, account_id, trigger, status, phase, started_at)
                   VALUES (?, ?, 'manual', 'running', 'import', ?)
                   ON CONFLICT(id) DO UPDATE SET status = 'running', phase = 'import', started_at = excluded.started_at,
                     error_code = NULL, error_message = NULL, finished_at = NULL""",
                (job_id, account_id, started_at),
            )
            self._record_event(job_id, "running", "import started", started_at)
            self.connection.commit()
            try:
                if cancel_event.is_set():
                    raise SyncCancelledError("sync cancelled before import started")
                stats = import_package(self.connection, package_root, archive_root, account_id, display_name)
                manifest = load_json(Path(package_root) / "manifest.json")
                export_id = manifest["export_id"]
                finished_at = int(time.time() * 1000)
                self.connection.execute(
                    """INSERT INTO sync_checkpoints(account_id, source_name, source_fingerprint, last_source_id, last_source_time, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(account_id, source_name) DO UPDATE SET source_fingerprint = excluded.source_fingerprint,
                         last_source_id = excluded.last_source_id, last_source_time = excluded.last_source_time, updated_at = excluded.updated_at""",
                    (account_id, source_name, export_id, export_id, finished_at, finished_at),
                )
                self.connection.execute(
                    "UPDATE sync_jobs SET status = 'completed', phase = 'complete', finished_at = ?, stats_json = ? WHERE id = ?",
                    (finished_at, json.dumps(stats, sort_keys=True), job_id),
                )
                self._record_event(job_id, "completed", "import completed", finished_at)
                self.connection.commit()
                return {"job_id": job_id, "status": "completed", "stats": stats}
            except SyncCancelledError as exc:
                finished_at = int(time.time() * 1000)
                self.connection.execute(
                    "UPDATE sync_jobs SET status = 'cancelled', phase = 'cancelled', finished_at = ?, error_code = 'SYNC_CANCELLED', error_message = ? WHERE id = ?",
                    (finished_at, str(exc), job_id),
                )
                self._record_event(job_id, "cancelled", str(exc), finished_at)
                self.connection.execute("UPDATE accounts SET status = 'ready', updated_at = ? WHERE id = ?", (finished_at, account_id))
                self.connection.commit()
                raise
            except Exception as exc:
                finished_at = int(time.time() * 1000)
                self.connection.execute(
                    "UPDATE sync_jobs SET status = 'failed', phase = 'import', finished_at = ?, error_code = 'IMPORT_FAILED', error_message = ? WHERE id = ?",
                    (finished_at, str(exc), job_id),
                )
                self._record_event(job_id, "failed", str(exc), finished_at)
                self.connection.execute("UPDATE accounts SET status = 'error', updated_at = ? WHERE id = ?", (finished_at, account_id))
                self.connection.commit()
                raise
        finally:
            self.connection.execute("DELETE FROM sync_locks WHERE lock_name = 'global' AND job_id = ?", (job_id,))
            self.connection.commit()
            self._lock.release()

    def _record_event(self, job_id: str, event_type: str, detail: str, created_at: int) -> None:
        self.connection.execute(
            "INSERT INTO sync_events(job_id, event_type, detail, created_at) VALUES (?, ?, ?, ?)",
            (job_id, event_type, detail, created_at),
        )

    def get_job(self, job_id: str) -> sqlite3.Row | None:
        return self.connection.execute("SELECT * FROM sync_jobs WHERE id = ?", (job_id,)).fetchone()

    def get_events(self, job_id: str) -> list[sqlite3.Row]:
        return self.connection.execute(
            "SELECT * FROM sync_events WHERE job_id = ? ORDER BY id",
            (job_id,),
        ).fetchall()
