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
    ) -> dict[str, object]:
        if not self._lock.acquire(blocking=False):
            raise SyncBusyError("another sync is already running")
        job_id = f"job_{uuid.uuid4().hex}"
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
                   ON CONFLICT(id) DO NOTHING""",
                (account_id, display_name or account_id, started_at, started_at),
            )
            self.connection.execute(
                "INSERT INTO sync_jobs(id, account_id, trigger, status, phase, started_at) VALUES (?, ?, 'manual', 'running', 'import', ?)",
                (job_id, account_id, started_at),
            )
            self.connection.commit()
            try:
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
                self.connection.commit()
                return {"job_id": job_id, "status": "completed", "stats": stats}
            except Exception as exc:
                finished_at = int(time.time() * 1000)
                self.connection.execute(
                    "UPDATE sync_jobs SET status = 'failed', phase = 'import', finished_at = ?, error_code = 'IMPORT_FAILED', error_message = ? WHERE id = ?",
                    (finished_at, str(exc), job_id),
                )
                self.connection.commit()
                raise
        finally:
            self.connection.execute("DELETE FROM sync_locks WHERE lock_name = 'global' AND job_id = ?", (job_id,))
            self.connection.commit()
            self._lock.release()

    def get_job(self, job_id: str) -> sqlite3.Row | None:
        return self.connection.execute("SELECT * FROM sync_jobs WHERE id = ?", (job_id,)).fetchone()
