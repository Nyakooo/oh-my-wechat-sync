import unittest

from archive_core.runtime import RuntimeManager, RuntimeStatus, RuntimeUnavailableError


class FakeRuntime:
    kind = "fake"

    def start(self, account_id, runtime_ref):
        return RuntimeStatus(account_id, self.kind, "running", runtime_ref)

    def stop(self, account_id, runtime_ref):
        return RuntimeStatus(account_id, self.kind, "stopped", runtime_ref)

    def status(self, account_id, runtime_ref):
        return RuntimeStatus(account_id, self.kind, "ready", runtime_ref)


class RuntimeManagerTests(unittest.TestCase):
    def test_dispatches_lifecycle_without_knowing_runtime_implementation(self) -> None:
        manager = RuntimeManager([FakeRuntime()])
        self.assertEqual(manager.start("account-a", "fake", "runtime-a").state, "running")
        self.assertEqual(manager.stop("account-a", "fake", "runtime-a").state, "stopped")
        self.assertEqual(manager.status("account-a", "fake", "runtime-a").state, "ready")

    def test_missing_adapter_is_explicitly_unavailable(self) -> None:
        with self.assertRaises(RuntimeUnavailableError):
            RuntimeManager().status("account-a", "wechat-on-cloud")


if __name__ == "__main__":
    unittest.main()
