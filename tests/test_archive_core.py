import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from archive_core import CURRENT_SCHEMA_VERSION, connect, initialize, import_package, search_messages


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "import-v0-minimal"


class ArchiveCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="wechat-archive-core-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.connection = connect(self.temp_dir / "archive.db")
        self.addCleanup(self.connection.close)
        initialize(self.connection)

    def test_first_import_creates_archive_and_search_index(self) -> None:
        stats = import_package(self.connection, FIXTURE, self.temp_dir / "data", "account-a", now_ms=1000)

        self.assertEqual(stats["messages_inserted"], 1)
        self.assertEqual(stats["attachments_inserted"], 1)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 1)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM attachments").fetchone()[0], 1)
        self.assertEqual(len(search_messages(self.connection, "account-a", "Synthetic")), 1)
        self.assertEqual(len(list((self.temp_dir / "data" / "media").iterdir())), 1)

    def test_repeat_import_is_idempotent(self) -> None:
        import_package(self.connection, FIXTURE, self.temp_dir / "data", "account-a", now_ms=1000)
        stats = import_package(self.connection, FIXTURE, self.temp_dir / "data", "account-a", now_ms=2000)

        self.assertEqual(stats["messages_inserted"], 0)
        self.assertEqual(stats["messages_updated"], 1)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 1)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM attachments").fetchone()[0], 1)
        self.assertEqual(stats["media_reused"], 1)

    def test_accounts_are_isolated_while_media_is_content_deduplicated(self) -> None:
        import_package(self.connection, FIXTURE, self.temp_dir / "data", "account-a", now_ms=1000)
        import_package(self.connection, FIXTURE, self.temp_dir / "data", "account-b", now_ms=1000)

        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0], 2)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 2)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM attachments").fetchone()[0], 2)
        self.assertEqual(len(list((self.temp_dir / "data" / "media").iterdir())), 1)

    def test_invalid_package_does_not_create_account(self) -> None:
        invalid = self.temp_dir / "invalid"
        shutil.copytree(FIXTURE, invalid)
        manifest = json.loads((invalid / "manifest.json").read_text(encoding="utf-8"))
        del manifest["files"]["messages.ndjson"]
        (invalid / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")

        with self.assertRaises(Exception):
            import_package(self.connection, invalid, self.temp_dir / "data", "account-a")
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0], 0)

    def test_media_failure_rolls_back_database_and_new_file(self) -> None:
        with patch("archive_core.importer.shutil.copyfile", side_effect=OSError("simulated media failure")):
            with self.assertRaises(OSError):
                import_package(self.connection, FIXTURE, self.temp_dir / "data", "account-a")

        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0], 0)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 0)
        self.assertEqual(list((self.temp_dir / "data" / "media").iterdir()), [])

    def test_schema_version_is_current_and_reinitialization_is_safe(self) -> None:
        initialize(self.connection)
        self.assertEqual(self.connection.execute("SELECT value FROM archive_meta WHERE key = 'schema_version'").fetchone()[0], str(CURRENT_SCHEMA_VERSION))


if __name__ == "__main__":
    unittest.main()
