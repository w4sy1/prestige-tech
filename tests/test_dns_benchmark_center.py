import os
from threading import Event
import unittest
from unittest.mock import patch

from prestige_core.dns_benchmark import benchmark, question, summary, validate_response
from prestige_core.dns_profiles import (PROFILES, discovery_candidates,
                                        get_profile, identify_provider)


class DnsBenchmarkCenterTests(unittest.TestCase):
    def test_system_and_gateway_candidates_are_distinct_and_deduplicated(self):
        rows = discovery_candidates([
            {"dns": ["192.168.1.1", "1.1.1.1", "bad"], "gateway": ["192.168.1.1"]},
            {"dns": ["1.1.1.1", "0.0.0.0"], "gateway": ["224.0.0.1"]},
        ])
        self.assertEqual([row["address"] for row in rows], ["192.168.1.1", "1.1.1.1"])
        self.assertEqual(len(rows[0]["sources"]), 2)
        self.assertEqual(rows[1]["sources"], ["Aktualny DNS systemu/DHCP"])

    def test_profile_copy_and_provider_identification(self):
        self.assertEqual(len(PROFILES), 8)
        profile = get_profile("cloudflare")
        profile["ipv4"].append("127.0.0.1")
        self.assertNotIn("127.0.0.1", PROFILES["cloudflare"]["ipv4"])
        self.assertEqual(identify_provider(["1.1.1.1"])["key"], "cloudflare")

    def test_benchmark_ranking_and_limits(self):
        with patch("prestige_core.dns_benchmark.query", side_effect=lambda server, *_: {
                "ms": 10 if server == "1.1.1.1" else 30,
                "status": "OK", "transport": "UDP"}) as query:
            result = benchmark(["1.1.1.1", "8.8.8.8"], ["example.com"], 3)
        self.assertEqual(query.call_count, 6)
        self.assertEqual(result["ranking"][0]["server"], "1.1.1.1")
        self.assertEqual(result["ranking"][0]["successful"], 3)
        with self.assertRaises(ValueError):
            benchmark(["1.1.1.1"], count=501)
        stopped = Event(); stopped.set()
        with self.assertRaises(RuntimeError):
            benchmark(["1.1.1.1"], count=3, cancel_event=stopped)

    def test_question_and_no_response_summary(self):
        self.assertTrue(question("example.com").endswith(b"\x00\x00\x01\x00\x01"))
        with self.assertRaises(ValueError):
            question("bad..name")
        self.assertIsNone(summary([{"status": "TIMEOUT", "ms": None}])["mean_ms"])


class DnsBenchmarkGuiTests(unittest.TestCase):
    def test_profile_fills_plan_without_apply(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_network_center.gui import NetworkCenterWindow
        app = QApplication.instance() or QApplication([])
        window = NetworkCenterWindow()
        window.dns_profile.setCurrentIndex(0)
        window.use_dns_profile()
        self.assertIn("1.1.1.1", window.dns_addresses.text())
        self.assertTrue(window.dns_benchmark_button.isEnabled())
        window.close()

    def test_adapter_read_exposes_discovered_dns_without_network_probe(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_network_center.gui import NetworkCenterWindow
        app = QApplication.instance() or QApplication([])
        window = NetworkCenterWindow(autoload=False)
        window.show_adapters([{"name": "Wi-Fi", "index": 3, "ipv4": ["192.168.1.2"],
                               "gateway": ["192.168.1.1"], "dns": ["1.1.1.1"]}])
        self.assertIn("1 adresów DNS", window.dns_benchmark_note.text())
        self.assertTrue(window.dns_include_system.isChecked())
        self.assertFalse(window.dns_include_gateway.isChecked())
        window.close()
