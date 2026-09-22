from __future__ import annotations

import sqlite3
import time
import uuid


def queue_initial_sync_after_login(
    connection: sqlite3.Connection,
    account_id: str,
) -> dict[str, object]:
    """Queue at most one initial archive job for a Runtime login success.

    Runtime adapters may call this for every authenticated status notification.
    The database constraint makes duplicate and concurrent notifications safe.
    This function only persists the job; it does not read WeChat data or run it.
    """
    account = connection.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if account is None:
        raise KeyError(f"account not found: {account_id}")

    now = int(time.time() * 1000)
    job_id = f"job_{uuid.uuid4().hex}"
    cursor = connection.execute(
        """INSERT OR IGNORE INTO sync_jobs(id, account_id, trigger, status, phase)
           VALUES (?, ?, 'initial', 'queued', 'queued')""",
        (job_id, account_id),
    )
    created = cursor.rowcount == 1
    if created:
        connection.execute(
            """INSERT INTO sync_events(job_id, event_type, detail, created_at)
               VALUES (?, 'initial_sync_queued', 'Runtime login succeeded; initial archive queued', ?)""",
            (job_id, now),
        )
    connection.commit()

    job = connection.execute(
        "SELECT id, account_id, trigger, status, phase FROM sync_jobs WHERE account_id = ? AND trigger = 'initial'",
        (account_id,),
    ).fetchone()
    if job is None:  # Defensive: the insert or its unique-index lookup must yield a row.
        raise RuntimeError("initial sync job was not persisted")
    return {**dict(job), "created": created}
