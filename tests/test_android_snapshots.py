import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.android_snapshots import compare_apps_snapshots, load_apps_snapshot


class AndroidSnapshotTest(unittest.TestCase):
    def test_offline_permission_change(self):
        before = {"serial": "device-1", "status": "COMPLETE", "apps": [
            {"package": "example.app", "granted_permissions": {"CAMERA": False}}]}
        after = {"serial": "device-1", "status": "COMPLETE", "apps": [
            {"package": "example.app", "granted_permissions": {"CAMERA": True}}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snapshot.json"
            path.write_text(json.dumps(before), encoding="utf-8")
            result = compare_apps_snapshots(load_apps_snapshot(path), after)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["changed"][0]["fields"]["granted_permissions"]["after"], {"CAMERA": True})
        after["status"] = "UNKNOWN"
        self.assertEqual(compare_apps_snapshots(before, after)["status"], "UNKNOWN")

    def test_different_devices_rejected(self):
        with self.assertRaises(ValueError):
            compare_apps_snapshots({"serial": "a", "apps": []}, {"serial": "b", "apps": []})


if __name__ == "__main__":
    unittest.main()
