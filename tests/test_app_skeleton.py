import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AppSkeletonTests(unittest.TestCase):
    def test_backend_and_web_entrypoints_exist(self) -> None:
        self.assertTrue((ROOT / "backend/app/main.py").is_file())
        self.assertTrue((ROOT / "web/package.json").is_file())
        self.assertTrue((ROOT / "web/src/App.vue").is_file())


if __name__ == "__main__":
    unittest.main()
