import tempfile
import unittest
from pathlib import Path

from archive_core.database import connect, initialize
from archive_core.importer import import_package
from tools.archive_snapshot import snapshot


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/import-v0-minimal"


class SnapshotTests(unittest.TestCase):
    def test_snapshot_contains_database_and_media_and_can_be_opened(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "archive.db"
            archive = root / "data"
            with connect(database) as connection:
                initialize(connection)
                import_package(connection, FIXTURE, archive, "account-a", now_ms=1000)
            result = snapshot(database, archive, root / "snapshot")
            self.assertEqual(result["media_files"], 1)
            with connect(root / "snapshot/archive.db") as restored:
                self.assertEqual(restored.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 1)
            self.assertTrue((root / "snapshot/media").is_dir())


if __name__ == "__main__":
    unittest.main()
