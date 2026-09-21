import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeploymentSecurityTests(unittest.TestCase):
    def test_compose_does_not_mount_docker_socket_and_import_is_read_only(self) -> None:
        compose = (ROOT / "deploy/compose.yaml").read_text()
        self.assertNotIn("docker.sock", compose)
        self.assertIn(":/imports:ro", compose)

    def test_security_document_records_missing_public_authentication(self) -> None:
        document = (ROOT / "docs/deployment-security.md").read_text()
        self.assertIn("尚未实现用户认证", document)
        self.assertIn("不能直接暴露到公网", document)


if __name__ == "__main__":
    unittest.main()
