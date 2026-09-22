import tempfile
import unittest
from pathlib import Path

from archive_core.database import connect
from archive_core.importer import search_messages
from tools.seed_demo import seed


class DemoSeedTests(unittest.TestCase):
    def test_seeds_synthetic_conversations_messages_and_media(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stats = seed(root / "archive.db", root / "data", "demo")
            self.assertEqual(stats["messages_inserted"], 6)
            with connect(root / "archive.db") as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM conversations WHERE account_id='demo'").fetchone()[0], 2)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM attachments WHERE account_id='demo'").fetchone()[0], 2)
                self.assertEqual(len(search_messages(connection, "demo", "weekend")), 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM messages WHERE content LIKE '%虚构%' OR content LIKE '%演示数据%' ").fetchone()[0], 3)

    def test_refuses_to_overwrite_existing_demo_account(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed(root / "archive.db", root / "data", "demo")
            with self.assertRaisesRegex(ValueError, "will not overwrite"):
                seed(root / "archive.db", root / "data", "demo")


if __name__ == "__main__":
    unittest.main()
