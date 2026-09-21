import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from archive_core.database import connect, initialize
from archive_core.importer import import_package, search_messages
from tools.archive_health import report
from tools.rebuild_fts import rebuild


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/import-v0-minimal"


class MaintenanceToolTests(unittest.TestCase):
    def test_health_report_detects_valid_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "archive.db"
            archive = root / "data"
            with connect(database) as connection:
                initialize(connection)
                import_package(connection, FIXTURE, archive, "account-a", now_ms=1000)
            result = report(database, archive)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["counts"]["orphan_media"], 0)

    def test_fts_rebuild_restores_search_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "archive.db"
            with connect(database) as connection:
                initialize(connection)
                import_package(connection, FIXTURE, root / "data", "account-a", now_ms=1000)
                connection.execute("DELETE FROM messages_fts")
                connection.commit()
                self.assertEqual(search_messages(connection, "account-a", "Synthetic"), [])
                self.assertEqual(rebuild(connection), 1)
                self.assertEqual(len(search_messages(connection, "account-a", "Synthetic")), 1)

    def test_health_cli_returns_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "archive.db"
            with connect(database) as connection:
                initialize(connection)
            result = subprocess.run(
                [sys.executable, "tools/archive_health.py", "--database", str(database), "--archive-root", str(root / "data")],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json.loads(result.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
