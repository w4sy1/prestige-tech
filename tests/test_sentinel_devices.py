import json
import os
import tempfile
import unittest
from pathlib import Path

from prestige_core.sentinel_devices import (assess_observations, correlate_devices,
                                            read_device_registry)


class SentinelDevicesTest(unittest.TestCase):
    def test_scan_registry_comparison_does_not_treat_cache_as_online(self):
        registry = {"status": "COMPLETE", "devices": [
            {"key": "aa:bb:cc:dd:ee:01", "mac": "aa:bb:cc:dd:ee:01", "ip": "192.168.1.2"},
            {"key": "aa:bb:cc:dd:ee:02", "mac": "aa:bb:cc:dd:ee:02", "ip": "192.168.1.3"}]}
        scan = {"status": "COMPLETE", "observed": [
            {"ip": "192.168.1.4", "mac": "aa:bb:cc:dd:ee:01", "evidence": "ICMP"},
            {"ip": "192.168.1.3", "mac": "aa:bb:cc:dd:ee:09", "evidence": "Nmap"},
            {"ip": "192.168.1.5", "mac": "aa:bb:cc:dd:ee:05", "evidence": "ICMP"},
            {"ip": "192.168.1.6", "mac": "aa:bb:cc:dd:ee:06", "evidence": "Cache — dostępność nieznana"}]}
        result = assess_observations(registry, scan)
        self.assertEqual([row["type"] for row in result["findings"]],
                         ["IP_CHANGE", "POSSIBLE_MAC_CHANGE", "NEW_DEVICE"])
        self.assertIn("nie dowodzi offline", result["note"])
        with self.assertRaises(ValueError):
            assess_observations({"status": "UNKNOWN", "devices": []}, scan)

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

    def test_network_center_shows_read_only_comparison(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_network_center.gui import NetworkCenterWindow
        app = QApplication.instance() or QApplication([])
        window = NetworkCenterWindow(autoload=False)
        window.sentinel_registry_result = {"status": "COMPLETE", "devices": []}
        window.last_discovery_result = {"status": "COMPLETE", "observed": [
            {"ip": "192.168.1.4", "mac": "aa:bb:cc:dd:ee:05", "evidence": "ICMP"}]}
        window.compare_sentinel_devices()
        self.assertIn("NEW_DEVICE", window.registry_comparison.toPlainText())
        window.close()
