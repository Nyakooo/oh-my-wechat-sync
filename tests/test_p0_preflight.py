import unittest
from pathlib import Path

from tools.p0_preflight import build_preflight


ROOT = Path(__file__).resolve().parents[1]


class P0PreflightTests(unittest.TestCase):
    def test_preflight_stays_blocked_without_external_sample(self) -> None:
        report = build_preflight(ROOT, run_tests=False)
        statuses = {item["name"]: item["status"] for item in report["checks"]}

        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["phase1_allowed"])
        self.assertEqual(statuses["required_docs"], "passed")
        self.assertEqual(statuses["synthetic_fixture"], "passed")
        self.assertEqual(statuses["external_sample"], "blocked")
        self.assertEqual(statuses["p0_manual_review"], "blocked")


if __name__ == "__main__":
    unittest.main()
