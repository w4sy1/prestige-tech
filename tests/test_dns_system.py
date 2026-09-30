import json
import os
import subprocess
import unittest
from types import SimpleNamespace

from prestige_core.dns_system import read_doh_state, system_dns_test


class DnsSystemTests(unittest.TestCase):
    def test_doh_read_reports_availability_without_guessing_usage(self):
        seen = []
        def runner(command, **kwargs):
            seen.append((command, kwargs))
            return SimpleNamespace(returncode=0, stdout=json.dumps({
                "available": True, "servers": [{"ServerAddress": "1.1.1.1",
                                                   "DohTemplate": "https://example.test/dns-query"}]}))
        result = read_doh_state(runner=runner, platform="nt")
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertIn("nie dowodzi", result["note"])
        self.assertIn("-EncodedCommand", seen[0][0])
        with self.assertRaises(RuntimeError):
            read_doh_state(platform="posix")

    def test_system_resolution_is_bounded_and_validated(self):
        def runner(command, **kwargs):
            self.assertEqual(command[-1], "example.com")
            self.assertEqual(kwargs["timeout"], 15)
            return SimpleNamespace(returncode=0, stdout='["93.184.215.14"]')
        result = system_dns_test(runner=runner)
        self.assertEqual(result["status"], "OK")
        with self.assertRaises(ValueError):
            system_dns_test("bad;command", runner=runner)
        unknown = system_dns_test(runner=lambda *_a, **_kw: (_ for _ in ()).throw(
            subprocess.TimeoutExpired("resolver", 15)))
        self.assertEqual(unknown["status"], "UNKNOWN")

    def test_gui_exposes_read_only_actions(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_network_center.gui import NetworkCenterWindow
        app = QApplication.instance() or QApplication([])
        window = NetworkCenterWindow(autoload=False)
        self.assertTrue(window.dns_doh_button.isEnabled())
        self.assertTrue(window.dns_system_button.isEnabled())
        window.close()
