import tempfile
import unittest
import shutil
import time
from pathlib import Path

from fastapi import HTTPException

from archive_core.database import connect, initialize
from archive_core.importer import import_package
from backend.app.api import AccountCreate, AccountUpdate, ImportSyncRequest, build_router, connection_factory_for


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/import-v0-minimal"


class ApiLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "archive.db"
        self.factory = connection_factory_for(self.db_path)
        with self.factory() as connection:
            initialize(connection)
            import_package(connection, FIXTURE, Path(self.temp_dir.name) / "archive", "account-a", now_ms=1700000000000)
        self.router = build_router(
            self.factory,
            Path(self.temp_dir.name) / "archive",
            Path(self.temp_dir.name) / "imports",
        )
        shutil.copytree(FIXTURE, Path(self.temp_dir.name) / "imports" / "minimal")
        self.handlers = {
            (route.path, method): route.endpoint
            for route in self.router.routes
            for method in route.methods
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_account_and_read_only_browse_handlers(self) -> None:
        with self.factory() as connection:
            accounts = self.handlers[("/api/v1/accounts", "GET")](connection)
            self.assertEqual(accounts[0]["id"], "account-a")
            conversations = self.handlers[("/api/v1/accounts/{account_id}/conversations", "GET")]("account-a", 50, 0, connection)
            self.assertEqual(len(conversations), 1)
            messages = self.handlers[("/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages", "GET")](
                "account-a", conversations[0]["id"], 100, 0, connection
            )
            self.assertEqual(messages[0]["content"], "Synthetic message")
            self.assertEqual(messages[0]["attachments"][0]["status"], "available")

    def test_create_update_and_search_handlers(self) -> None:
        with self.factory() as connection:
            created = self.handlers[("/api/v1/accounts", "POST")](AccountCreate(id="account-b", display_name="工作微信"), connection)
            self.assertEqual(created["status"], "pending")
            updated = self.handlers[("/api/v1/accounts/{account_id}", "PATCH")]("account-b", AccountUpdate(display_name="新名称"), connection)
            self.assertEqual(updated["display_name"], "新名称")
            result = self.handlers[("/api/v1/search", "GET")](
                "account-a",
                "Synthetic",
                50,
                None,
                None,
                None,
                None,
                connection,
            )
            self.assertEqual(result[0]["source_msg_id"], "msg-1")

    def test_delete_requires_confirmation_and_removes_account_rows(self) -> None:
        with self.factory() as connection:
            delete = self.handlers[("/api/v1/accounts/{account_id}", "DELETE")]
            with self.assertRaises(HTTPException) as context:
                delete("account-a", False, connection)
            self.assertEqual(context.exception.status_code, 400)
            self.assertEqual(delete("account-a", True, connection), {"deleted": True, "account_id": "account-a"})
            self.assertEqual(self.handlers[("/api/v1/accounts", "GET")](connection), [])

    def test_missing_account_is_rejected(self) -> None:
        with self.factory() as connection:
            with self.assertRaises(HTTPException) as context:
                self.handlers[("/api/v1/accounts/{account_id}", "GET")]("missing", connection)
            self.assertEqual(context.exception.status_code, 404)

    def test_import_sync_endpoint_uses_named_package_under_configured_root(self) -> None:
        with self.factory() as connection:
            run_sync = self.handlers[("/api/v1/accounts/{account_id}/sync/import", "POST")]
            result = run_sync("account-a", ImportSyncRequest(package_name="minimal"), connection)
            self.assertEqual(result["status"], "queued")
            jobs = []
            for _ in range(40):
                jobs = self.handlers[("/api/v1/accounts/{account_id}/sync/jobs", "GET")]("account-a", 20, connection)
                if jobs and jobs[0]["status"] == "completed":
                    break
                time.sleep(0.05)
            self.assertEqual(jobs[0]["status"], "completed")
            events = self.handlers[("/api/v1/sync/jobs/{job_id}/events", "GET")](result["job_id"], connection)
            self.assertEqual([event["event_type"] for event in events], ["queued", "running", "completed"])

    def test_cancel_completed_sync_is_safe(self) -> None:
        with self.factory() as connection:
            run_sync = self.handlers[("/api/v1/accounts/{account_id}/sync/import", "POST")]
            result = run_sync("account-a", ImportSyncRequest(package_name="minimal"), connection)
            for _ in range(40):
                job = self.handlers[("/api/v1/sync/jobs/{job_id}", "GET")](result["job_id"], connection)
                if job["status"] == "completed":
                    break
                time.sleep(0.05)
            cancel = self.handlers[("/api/v1/sync/jobs/{job_id}/cancel", "POST")](result["job_id"], connection)
            self.assertEqual(cancel["status"], "completed")


if __name__ == "__main__":
    unittest.main()
