import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.sentinel_devices import correlate_devices, read_device_registry


class SentinelDevicesTest(unittest.TestCase):
    def test_correlates_legacy_lists_without_online_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            known_path = Path(folder) / "known.json"
            trusted_path = Path(folder) / "trusted.json"
            known_path.write_text(json.dumps([{"Key": "AA", "IP": "192.0.2.1", "Name": "Host"}]), encoding="utf-8")
            trusted_path.write_text(json.dumps([{"Key": "AA", "IP": "192.0.2.2"},
                                                {"Key": "BB", "IP": "192.0.2.3"}]), encoding="utf-8")
            result = correlate_devices(read_device_registry(known_path), read_device_registry(trusted_path))
            self.assertEqual(len(result["devices"]), 2)
            self.assertTrue(result["devices"][0]["ip_mismatch"])
            self.assertFalse(result["devices"][1]["known"])

    def test_invalid_rows_degrade_quality(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "known.json"
            path.write_text('[{"Key":"A"}, {}]', encoding="utf-8")
            result = read_device_registry(path)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["invalid_rows"], 1)
