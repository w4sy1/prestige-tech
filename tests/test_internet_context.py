import json
from types import SimpleNamespace
import unittest

from prestige_core.internet_context import correlate_diagnostic, parse_wifi, read_context


class InternetContextTest(unittest.TestCase):
    def test_correlates_wifi_without_claiming_cause(self):
        diagnostic = {"status": "COMPLETE", "gateway": {"packet_loss_percent": 30},
                      "internet": {"packet_loss_percent": 40}}
        context = {"status": "COMPLETE", "wifi": {"signal_percent": 25,
                   "estimated_rssi_dbm": -87.5}}
        result = correlate_diagnostic(diagnostic, context)
        self.assertEqual(result["category"], "słaby sygnał i straty do bramy")
        self.assertIn("nie dowodzą przyczyny", result["note"])
        self.assertEqual(correlate_diagnostic(diagnostic, {"wifi": {}})["status"], "UNKNOWN")

    def test_wifi_is_explicit_estimate(self):
        result = parse_wifi("Sygnał : 70%\nSzybkość odbierania : 144,4")
        self.assertEqual(result["signal_percent"], 70)
        self.assertEqual(result["estimated_rssi_dbm"], -65)
        self.assertIn("estimate", result["rssi_kind"])

    def test_read_context_normalizes_single_interface_and_dns(self):
        payload = {"gateway": "192.168.1.1", "interfaces": {
            "Description": "Ethernet", "DNSServerSearchOrder": ["1.1.1.1", "bad"]},
            "links": {"Name": "Ethernet", "Status": "Up"}}
        def runner(command, **kwargs):
            if command[0] == "netsh":
                return SimpleNamespace(returncode=0, stdout="Signal : 50%")
            self.assertIn("-EncodedCommand", command)
            return SimpleNamespace(returncode=0, stdout=json.dumps(payload))
        result = read_context(runner=runner, platform="nt")
        self.assertEqual(result["gateway"], "192.168.1.1")
        self.assertEqual(result["dns_servers"], ["1.1.1.1"])
        self.assertEqual(result["wifi"]["signal_percent"], 50)
