import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.network_dns_change import apply_dns_change, plan_dns_change, rollback_dns_change


class FakeDns:
    def __init__(self):
        self.state = {"index": 7, "automatic": True, "servers": ["192.0.2.53"]}
        self.fail_after_change = False
        self.calls = []

    def snapshot(self, index):
        self.calls.append(("snapshot", index))
        return dict(self.state)

    def set_dns(self, index, servers):
        self.calls.append(("set", index, servers))
        self.state = {"index": index, "automatic": servers is None,
                      "servers": ["192.0.2.53"] if servers is None else list(servers)}
        if self.fail_after_change:
            self.fail_after_change = False
            raise RuntimeError("response lost")


class NetworkDnsChangeTest(unittest.TestCase):
    def test_plan_does_not_change_dns(self):
        backend = FakeDns()
        plan = plan_dns_change(7, ["1.1.1.1"], backend)
        self.assertTrue(plan["change_needed"])
        self.assertFalse(any(call[0] == "set" for call in backend.calls))

    def test_apply_backup_and_conditional_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dns-backup.json"
            backend = FakeDns()
            result = apply_dns_change(7, ["1.1.1.1", "8.8.8.8"], path, backend)
            self.assertEqual(result["status"], "APPLIED")
            self.assertEqual(json.loads(path.read_text())["status"], "APPLIED")
            self.assertEqual(rollback_dns_change(path, backend)["status"], "PLAN")
            backend.state["servers"] = ["9.9.9.9"]
            with self.assertRaises(RuntimeError):
                rollback_dns_change(path, backend, apply=True)
            self.assertEqual(backend.state["servers"], ["9.9.9.9"])
            backend.state["servers"] = ["1.1.1.1", "8.8.8.8"]
            self.assertEqual(rollback_dns_change(path, backend, apply=True)["status"], "ROLLED_BACK")
            self.assertTrue(backend.state["automatic"])

    def test_failure_after_change_restores_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dns-backup.json"
            backend = FakeDns()
            backend.fail_after_change = True
            with self.assertRaises(RuntimeError):
                apply_dns_change(7, ["1.1.1.1"], path, backend)
            self.assertTrue(backend.state["automatic"])
            self.assertEqual(json.loads(path.read_text())["status"], "ROLLED_BACK_AFTER_ERROR")

    def test_recovery_from_prepared_backup_only_if_current_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dns.json"
            backend = FakeDns()
            apply_dns_change(7, ["1.1.1.1"], path, backend)
            record = json.loads(path.read_text())
            record["status"] = "PREPARED"
            path.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(rollback_dns_change(path, backend)["backup_status"], "PREPARED")
            backend.state["servers"] = ["9.9.9.9"]
            with self.assertRaises(RuntimeError):
                rollback_dns_change(path, backend, apply=True)
            backend.state["servers"] = ["1.1.1.1"]
            self.assertEqual(rollback_dns_change(path, backend, apply=True)["status"], "ROLLED_BACK")

    def test_refuses_existing_backup_or_invalid_dns(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "backup.json"
            path.write_text("unchanged", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                apply_dns_change(7, ["1.1.1.1"], path, FakeDns())
            self.assertEqual(path.read_text(encoding="utf-8"), "unchanged")
            with self.assertRaises(ValueError):
                plan_dns_change(7, ["1.1.1.1", "1.1.1.1"], FakeDns())
