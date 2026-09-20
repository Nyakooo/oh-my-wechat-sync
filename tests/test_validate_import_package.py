import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.validate_import_package import ValidationError, validate


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "import-v0-minimal"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update_manifest_file_hash(package: Path, file_name: str) -> None:
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][file_name]["sha256"] = sha256(package / file_name)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ImportPackageValidatorTests(unittest.TestCase):
    def copy_fixture(self) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix="wechat-import-test-"))
        package = temp_dir / "package"
        shutil.copytree(FIXTURE, package)
        self.addCleanup(shutil.rmtree, temp_dir, ignore_errors=True)
        return package

    def test_valid_synthetic_fixture(self) -> None:
        counts = validate(FIXTURE)
        self.assertEqual(counts["messages.ndjson"], 1)
        self.assertEqual(counts["attachments.ndjson"], 1)
        self.assertEqual(counts["conversation-members.ndjson"], 1)

    def test_rejects_manifest_hash_mismatch(self) -> None:
        package = self.copy_fixture()
        messages = package / "messages.ndjson"
        messages.write_text(messages.read_text(encoding="utf-8").replace("Synthetic message", "Tampered message"), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "manifest hash mismatch: messages.ndjson"):
            validate(package)

    def test_rejects_unknown_conversation_reference(self) -> None:
        package = self.copy_fixture()
        messages = package / "messages.ndjson"
        messages.write_text(messages.read_text(encoding="utf-8").replace('"chat-1"', '"missing-chat"'), encoding="utf-8")
        update_manifest_file_hash(package, "messages.ndjson")
        with self.assertRaisesRegex(ValidationError, "unknown source_chat_id"):
            validate(package)

    def test_rejects_unknown_member_reference(self) -> None:
        package = self.copy_fixture()
        members = package / "conversation-members.ndjson"
        members.write_text(members.read_text(encoding="utf-8").replace('"contact-1"', '"missing-contact"'), encoding="utf-8")
        update_manifest_file_hash(package, "conversation-members.ndjson")
        with self.assertRaisesRegex(ValidationError, "unknown source_contact_id"):
            validate(package)

    def test_rejects_undeclared_optional_members_file(self) -> None:
        package = self.copy_fixture()
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        del manifest["files"]["conversation-members.ndjson"]
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "optional file must be declared"):
            validate(package)

    def test_rejects_duplicate_member_pair(self) -> None:
        package = self.copy_fixture()
        members = package / "conversation-members.ndjson"
        original = members.read_text(encoding="utf-8")
        members.write_text(original + original, encoding="utf-8")
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"]["conversation-members.ndjson"]["records"] = 2
        manifest["files"]["conversation-members.ndjson"]["sha256"] = sha256(members)
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "duplicate member pair"):
            validate(package)

    def test_accepts_package_without_optional_members_file(self) -> None:
        package = self.copy_fixture()
        (package / "conversation-members.ndjson").unlink()
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        del manifest["files"]["conversation-members.ndjson"]
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        counts = validate(package)
        self.assertNotIn("conversation-members.ndjson", counts)

    def test_rejects_media_path_traversal(self) -> None:
        package = self.copy_fixture()
        attachments = package / "attachments.ndjson"
        attachments.write_text(attachments.read_text(encoding="utf-8").replace('"path":"media/', '"path":"../'), encoding="utf-8")
        update_manifest_file_hash(package, "attachments.ndjson")
        with self.assertRaisesRegex(ValidationError, "media path must be under media/"):
            validate(package)

    def test_rejects_media_path_outside_media_directory(self) -> None:
        package = self.copy_fixture()
        attachments = package / "attachments.ndjson"
        record = json.loads(attachments.read_text(encoding="utf-8"))
        record["path"] = "contacts.ndjson"
        attachments.write_text(json.dumps(record) + "\n", encoding="utf-8")
        update_manifest_file_hash(package, "attachments.ndjson")
        with self.assertRaisesRegex(ValidationError, "media path must be under media/"):
            validate(package)

    def test_rejects_symlink_media(self) -> None:
        package = self.copy_fixture()
        media = next((package / "media").iterdir())
        linked = package / "media" / "linked-media"
        try:
            linked.symlink_to(media.name)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        attachments = package / "attachments.ndjson"
        record = json.loads(attachments.read_text(encoding="utf-8"))
        record["path"] = "media/linked-media"
        attachments.write_text(json.dumps(record) + "\n", encoding="utf-8")
        update_manifest_file_hash(package, "attachments.ndjson")
        with self.assertRaisesRegex(ValidationError, "symbolic links are not allowed"):
            validate(package)

    def test_rejects_media_hash_mismatch(self) -> None:
        package = self.copy_fixture()
        media = next((package / "media").iterdir())
        media.write_text("tampered-media\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "media hash mismatch"):
            validate(package)

    def test_rejects_media_size_mismatch(self) -> None:
        package = self.copy_fixture()
        attachments = package / "attachments.ndjson"
        attachments.write_text(attachments.read_text(encoding="utf-8").replace('"size":16', '"size":15'), encoding="utf-8")
        update_manifest_file_hash(package, "attachments.ndjson")
        with self.assertRaisesRegex(ValidationError, "media size mismatch"):
            validate(package)

    def test_rejects_unsupported_source_kind(self) -> None:
        package = self.copy_fixture()
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source"]["kind"] = "unknown-source"
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "source.kind is unsupported"):
            validate(package)

    def test_rejects_timestamp_without_timezone(self) -> None:
        package = self.copy_fixture()
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["created_at"] = "2026-09-20T00:00:00"
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "must include a timezone"):
            validate(package)

    def test_rejects_boolean_manifest_version(self) -> None:
        package = self.copy_fixture()
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["format_version"] = False
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "only manifest.format_version 0 is supported"):
            validate(package)

    def test_rejects_boolean_message_timestamp(self) -> None:
        package = self.copy_fixture()
        messages = package / "messages.ndjson"
        record = json.loads(messages.read_text(encoding="utf-8"))
        record["source_created_at"] = True
        messages.write_text(json.dumps(record) + "\n", encoding="utf-8")
        update_manifest_file_hash(package, "messages.ndjson")
        with self.assertRaisesRegex(ValidationError, "source_created_at must be an integer"):
            validate(package)

    def test_rejects_boolean_media_size(self) -> None:
        package = self.copy_fixture()
        attachments = package / "attachments.ndjson"
        record = json.loads(attachments.read_text(encoding="utf-8"))
        record["size"] = True
        attachments.write_text(json.dumps(record) + "\n", encoding="utf-8")
        update_manifest_file_hash(package, "attachments.ndjson")
        with self.assertRaisesRegex(ValidationError, "size must be a non-negative integer"):
            validate(package)


if __name__ == "__main__":
    unittest.main()
