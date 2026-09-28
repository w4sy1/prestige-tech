import json
import tempfile
from pathlib import Path
import unittest

from prestige_core.network_snapshot import compare_snapshots, make_snapshot, save_snapshot


class NetworkSnapshotTests(unittest.TestCase):
    def test_exclusive_save_and_incomplete_observation(self):
        snapshot = make_snapshot(neighbors=[], adapters=[], captured_at="2026-09-27T00:00:00+00:00")
        self.assertFalse(snapshot["observation_complete"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            save_snapshot(snapshot, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), snapshot)
            with self.assertRaises(FileExistsError):
                save_snapshot(snapshot, path)

    def test_comparison_does_not_call_missing_device_offline(self):
        earlier = make_snapshot(neighbors=[{"mac": "aa", "ips": ["192.0.2.2"]}], adapters=[])
        later = make_snapshot(neighbors=[{"mac": "bb", "ips": ["192.0.2.3"]}], adapters=[])
        result = compare_snapshots(earlier, later)
        self.assertEqual(result["newly_observed"][0]["mac"], "bb")
        self.assertEqual(result["not_observed_now"][0]["mac"], "aa")
        self.assertIn("nie potwierdza", result["note"])

    def test_compares_legacy_host_snapshot_with_new_format(self):
        old = {"schema_version": 1, "hosts": {"aa:bb:cc:dd:ee:02": {
            "mac": "aa:bb:cc:dd:ee:02", "ips": ["192.168.1.2"],
            "hostname": "old", "vendor": "A"}}}
        new = make_snapshot(neighbors=[{"mac": "aa:bb:cc:dd:ee:02",
                                        "ips": ["192.168.1.3"], "hostname": "new", "vendor": "B"}],
                            adapters=[])
        result = compare_snapshots(old, new)
        self.assertEqual(result["changed_ips"][0]["mac"], "aa:bb:cc:dd:ee:02")
        self.assertEqual(result["changed_hostnames"][0]["after"], "new")
        self.assertEqual(result["changed_vendors"][0]["after"], "B")

    def test_hyphen_mac_and_multiple_ip_rows_match_legacy_host(self):
        old = {"schema_version": 1, "hosts": {"aa:bb:cc:dd:ee:02": {
            "mac": "AA:BB:CC:DD:EE:02", "ips": ["192.168.1.2", "192.168.1.3"],
            "hostname": "device", "vendor": "vendor"}}}
        new = make_snapshot(neighbors=[
            {"mac": "AA-BB-CC-DD-EE-02", "ips": ["192.168.1.3"], "hostname": "device"},
            {"mac": "aa-bb-cc-dd-ee-02", "ips": ["192.168.1.2"], "vendor": "vendor"},
        ], adapters=[])
        result = compare_snapshots(old, new)
        self.assertEqual(result["newly_observed"], [])
        self.assertEqual(result["not_observed_now"], [])
        self.assertEqual(result["changed_ips"], [])
        self.assertEqual(result["changed_hostnames"], [])
        self.assertEqual(result["changed_vendors"], [])


if __name__ == "__main__":
    unittest.main()
