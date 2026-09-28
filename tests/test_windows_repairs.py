import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from prestige_core.windows_repairs import OPERATIONS, plan_repair, run_repair


class WindowsRepairTests(unittest.TestCase):
    def test_all_legacy_operations_have_bounded_plan(self):
        self.assertEqual(set(OPERATIONS), {"sfc", "dism-scan", "dism-restore", "flush-dns",
                                           "winsock-reset", "dhcp-renew"})
        for operation in OPERATIONS:
            plan = plan_repair(operation)
            self.assertEqual(plan["status"], "PLAN")
            self.assertFalse(plan["rollback_available"])
            self.assertGreater(plan["timeout_seconds"], 0)
        with self.assertRaises(ValueError):
            plan_repair("powershell")

    def test_execution_writes_snapshot_before_fixed_command(self):
        with tempfile.TemporaryDirectory() as directory:
            seen = []
            def runner(command, **kwargs):
                journals = list(Path(directory).glob("prestige-repair-*.json"))
                self.assertEqual(len(journals), 1)
                self.assertEqual(json.loads(journals[0].read_text(encoding="utf-8"))["status"], "STARTED")
                seen.append(command)
                return SimpleNamespace(returncode=3010, stdout="Restart", stderr="")
            result = run_repair("winsock-reset", directory, accept_no_rollback=True,
                                runner=runner, admin_check=lambda: True,
                                snapshot={"sections": {}}, platform="nt")
            self.assertEqual(seen, [["netsh.exe", "winsock", "reset"]])
            self.assertEqual(result["status"], "COMPLETE")
            self.assertTrue(result["restart_required"])
            self.assertEqual(json.loads(Path(result["journal"]).read_text(encoding="utf-8"))["status"], "COMPLETE")

    def test_no_consent_or_admin_never_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            def forbidden(*_args, **_kwargs):
                self.fail("Nie wolno uruchamiać polecenia")
            with self.assertRaises(ValueError):
                run_repair("sfc", directory, runner=forbidden, admin_check=lambda: True,
                           snapshot={}, platform="nt")
            with self.assertRaises(PermissionError):
                run_repair("sfc", directory, accept_no_rollback=True, runner=forbidden,
                           admin_check=lambda: False, snapshot={}, platform="nt")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_failed_command_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_repair("flush-dns", directory, accept_no_rollback=True,
                                runner=lambda *_a, **_k: SimpleNamespace(returncode=1, stdout="", stderr="error"),
                                admin_check=lambda: True, snapshot={}, platform="nt")
            self.assertEqual(result["status"], "FAILED")
            self.assertEqual(json.loads(Path(result["journal"]).read_text(encoding="utf-8"))["error_tail"], "error")


if __name__ == "__main__":
    unittest.main()
