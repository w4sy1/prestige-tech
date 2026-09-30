import json
import tempfile
from pathlib import Path
import unittest

from prestige_core.network_snapshot import (compare_snapshots, make_snapshot, save_snapshot,
                                            snapshot_from_json_list)


class NetworkSnapshotTests(unittest.TestCase):
    def test_snapshot_from_json_list_keeps_source_and_does_not_claim_online(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "devices.json"
            source.write_text('[{"mac":"00:11:22:33:44:55","ip":"192.0.2.5"}]', encoding="utf-8")
            snapshot = snapshot_from_json_list(source)
            self.assertEqual(snapshot["neighbors"][0]["ips"], ["192.0.2.5"])
            self.assertEqual(snapshot["adapters"], [])
            self.assertFalse(snapshot["observation_complete"])
            self.assertIn("lista JSON", snapshot["source"])
            self.assertTrue(source.exists())

    def test_discovery_enriches_snapshot_without_online_claim(self):
        neighbors = [{"mac": "aa:bb:cc:dd:ee:02", "ips": ["192.168.1.2"]}]
        scan = {"scope": "192.168.1.0/24", "status": "UNKNOWN", "probed": 253,
                "responsive": [{"ip": "192.168.1.3", "mac": "aa:bb:cc:dd:ee:02"}],
                "nmap_found": 1, "observed": [
                    {"ip": "192.168.1.3", "mac": "aa:bb:cc:dd:ee:02",
                     "hostname": "host", "vendor": "Vendor", "evidence": "ICMP"},
                    {"ip": "192.168.1.4", "mac": None, "evidence": "Nmap"},
                ]}
        snapshot = make_snapshot(neighbors=neighbors, adapters=[], discovery=scan)
        self.assertEqual(snapshot["neighbors"][0]["ips"], ["192.168.1.2", "192.168.1.3"])
        self.assertEqual(snapshot["neighbors"][0]["hostname"], "host")
        self.assertEqual(snapshot["discovery"]["responsive_without_mac"], ["192.168.1.4"])
        self.assertFalse(snapshot["observation_complete"])
        self.assertEqual(neighbors[0]["ips"], ["192.168.1.2"])

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
