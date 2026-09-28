import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.network_mtu_change import (apply_mtu_change, plan_mtu_change,
                                              rollback_mtu_change)


class FakeMtu:
    def __init__(self):
        self.state = {"index": 7, "mtu": 1500}
        self.fail_after_change = False

    def snapshot_mtu(self, index):
        return dict(self.state)

    def set_mtu(self, index, value):
        self.state = {"index": index, "mtu": value}
        if self.fail_after_change:
            self.fail_after_change = False
            raise RuntimeError("response lost")


def probe(_):
    return {"status": "ESTIMATE", "estimated_ipv4_mtu": 1400}


class NetworkMtuChangeTest(unittest.TestCase):
    def test_plan_and_conditional_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = FakeMtu()
            plan = plan_mtu_change(7, 1400, "192.0.2.1", backend)
            self.assertTrue(plan["change_needed"])
            self.assertEqual(backend.state["mtu"], 1500)
            path = Path(folder) / "mtu.json"
            result = apply_mtu_change(7, 1400, "192.0.2.1", path, backend, probe=probe)
            self.assertEqual(result["status"], "APPLIED")
            self.assertEqual(rollback_mtu_change(path, backend)["status"], "PLAN")
            backend.state["mtu"] = 1300
            with self.assertRaises(RuntimeError):
                rollback_mtu_change(path, backend, apply=True)
            backend.state["mtu"] = 1400
            self.assertEqual(rollback_mtu_change(path, backend, apply=True)["status"], "ROLLED_BACK")
            self.assertEqual(backend.state["mtu"], 1500)

    def test_failed_post_probe_recovers_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mtu.json"
            backend = FakeMtu()
            calls = []
            def failing_probe(_):
                calls.append(True)
                return probe(_) if len(calls) == 1 else {"status": "UNKNOWN"}
            with self.assertRaises(RuntimeError):
                apply_mtu_change(7, 1400, "192.0.2.1", path, backend, probe=failing_probe)
            self.assertEqual(backend.state["mtu"], 1500)
            self.assertEqual(json.loads(path.read_text())["status"], "ROLLED_BACK_AFTER_ERROR")

    def test_no_probe_means_no_change(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mtu.json"
            backend = FakeMtu()
            with self.assertRaises(RuntimeError):
                apply_mtu_change(7, 1400, "192.0.2.1", path, backend,
                                 probe=lambda _: {"status": "UNKNOWN"})
            self.assertFalse(path.exists())
            self.assertEqual(backend.state["mtu"], 1500)

    def test_recovery_from_prepared_backup_only_if_current_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mtu.json"
            backend = FakeMtu()
            apply_mtu_change(7, 1400, "192.0.2.1", path, backend, probe=probe)
            record = json.loads(path.read_text())
            record["status"] = "PREPARED"
            path.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(rollback_mtu_change(path, backend)["backup_status"], "PREPARED")
            backend.state["mtu"] = 1300
            with self.assertRaises(RuntimeError):
                rollback_mtu_change(path, backend, apply=True)
            backend.state["mtu"] = 1400
            self.assertEqual(rollback_mtu_change(path, backend, apply=True)["status"], "ROLLED_BACK")

    def test_rejects_unsupported_jumbo_and_existing_backup(self):
        with self.assertRaises(ValueError):
            plan_mtu_change(7, 9000, "192.0.2.1", FakeMtu())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mtu.json"
            path.write_text("old", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                apply_mtu_change(7, 1400, "192.0.2.1", path, FakeMtu(), probe=probe)
            self.assertEqual(path.read_text(), "old")
