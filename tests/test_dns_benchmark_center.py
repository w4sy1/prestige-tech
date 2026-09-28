import os
from threading import Event
import unittest
from unittest.mock import patch

from prestige_core.dns_benchmark import benchmark, question, summary, validate_response
from prestige_core.dns_profiles import PROFILES, get_profile, identify_provider


class DnsBenchmarkCenterTests(unittest.TestCase):
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
