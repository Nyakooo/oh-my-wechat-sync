import shutil
import tempfile
import unittest
from pathlib import Path

from archive_core import SyncOrchestrator, connect, initialize


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "import-v0-minimal"


class SyncOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="wechat-sync-test-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.connection = connect(self.temp_dir / "archive.db")
        self.addCleanup(self.connection.close)
        initialize(self.connection)
        self.orchestrator = SyncOrchestrator(self.connection)

    def test_package_sync_writes_job_and_checkpoint(self) -> None:
        result = self.orchestrator.sync_package(FIXTURE, self.temp_dir / "data", "account-a")

        self.assertEqual(result["status"], "completed")
        job = self.orchestrator.get_job(result["job_id"])
        self.assertEqual(job["status"], "completed")
        checkpoint = self.connection.execute("SELECT source_fingerprint FROM sync_checkpoints WHERE account_id = 'account-a'").fetchone()
        self.assertEqual(checkpoint[0], "synthetic-export-1")

    def test_failed_package_sync_records_failed_job(self) -> None:
        invalid = self.temp_dir / "invalid"
        shutil.copytree(FIXTURE, invalid)
        (invalid / "media").iterdir().__next__().unlink()

        with self.assertRaises(Exception):
            self.orchestrator.sync_package(invalid, self.temp_dir / "data", "account-a")

        job = self.connection.execute("SELECT status, error_code FROM sync_jobs ORDER BY started_at DESC LIMIT 1").fetchone()
        self.assertEqual(tuple(job), ("failed", "IMPORT_FAILED"))
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM sync_checkpoints").fetchone()[0], 0)

    def test_repeated_package_sync_is_idempotent(self) -> None:
        self.orchestrator.sync_package(FIXTURE, self.temp_dir / "data", "account-a")
        self.orchestrator.sync_package(FIXTURE, self.temp_dir / "data", "account-a")

        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 1)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM sync_jobs").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
