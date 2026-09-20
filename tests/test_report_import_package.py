import json
import unittest
from pathlib import Path

from tools.report_import_package import build_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "import-v0-minimal"


class ImportPackageReportTests(unittest.TestCase):
    def test_report_is_redacted_and_counts_records(self) -> None:
        report = build_report(FIXTURE)
        serialized = json.dumps(report, ensure_ascii=False)

        self.assertEqual(report["status"], "valid")
        self.assertEqual(report["records"]["messages.ndjson"], 1)
        self.assertEqual(report["records"]["conversation-members.ndjson"], 1)
        self.assertEqual(report["media"]["attachment_count"], 1)
        self.assertEqual(report["media"]["total_bytes"], 16)
        self.assertEqual(report["media"]["kinds"], {"file": 1})
        self.assertNotIn("synthetic-account-1", serialized)
        self.assertNotIn("Synthetic message", serialized)


if __name__ == "__main__":
    unittest.main()
