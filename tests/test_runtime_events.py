import shutil
import tempfile
import unittest
from pathlib import Path

from archive_core.database import connect, initialize
from archive_core.runtime_events import queue_initial_sync_after_login


class RuntimeEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="wechat-runtime-event-test-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.connection = connect(self.temp_dir / "archive.db")
        self.addCleanup(self.connection.close)
        initialize(self.connection)
        self.connection.execute(
            """INSERT INTO accounts(id, display_name, runtime_kind, status, created_at, updated_at)
               VALUES ('account-a', 'Test account', 'candidate', 'pending', 1, 1)"""
        )
        self.connection.commit()

    def test_first_login_queues_one_initial_job(self) -> None:
        first = queue_initial_sync_after_login(self.connection, "account-a")
        repeated = queue_initial_sync_after_login(self.connection, "account-a")

        self.assertEqual(first["trigger"], "initial")
        self.assertEqual(first["status"], "queued")
        self.assertTrue(first["created"])
        self.assertFalse(repeated["created"])
        self.assertEqual(first["id"], repeated["id"])
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM sync_jobs WHERE account_id = 'account-a' AND trigger = 'initial'"
            ).fetchone()[0],
            1,
        )
        event = self.connection.execute(
            "SELECT event_type FROM sync_events WHERE job_id = ?", (first["id"],)
        ).fetchone()
        self.assertEqual(event[0], "initial_sync_queued")

    def test_login_event_for_unknown_account_is_rejected(self) -> None:
        with self.assertRaisesRegex(KeyError, "account not found"):
            queue_initial_sync_after_login(self.connection, "missing")

    def test_manual_jobs_do_not_conflict_with_initial_job(self) -> None:
        initial = queue_initial_sync_after_login(self.connection, "account-a")
        self.connection.execute(
            """INSERT INTO sync_jobs(id, account_id, trigger, status, phase)
               VALUES ('manual-1', 'account-a', 'manual', 'queued', 'queued')"""
        )
        self.connection.commit()
        repeated = queue_initial_sync_after_login(self.connection, "account-a")

        self.assertEqual(repeated["id"], initial["id"])
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM sync_jobs WHERE account_id = 'account-a'").fetchone()[0],
            2,
        )

    def test_schema_v1_database_upgrades_initial_job_constraint(self) -> None:
        self.connection.execute("UPDATE archive_meta SET value = '1' WHERE key = 'schema_version'")
        self.connection.execute("DROP INDEX idx_sync_jobs_one_initial_per_account")
        self.connection.commit()

        initialize(self.connection)

        version = self.connection.execute(
            "SELECT value FROM archive_meta WHERE key = 'schema_version'"
        ).fetchone()[0]
        index = self.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'idx_sync_jobs_one_initial_per_account'"
        ).fetchone()
        self.assertEqual(version, "2")
        self.assertIsNotNone(index)


if __name__ == "__main__":
    unittest.main()
