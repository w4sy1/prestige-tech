from types import SimpleNamespace
import unittest

from prestige_core.internet_diagnostic import classify, diagnose, http_probe, mtu_probe, ping_sample, summarize


class InternetDiagnosticTests(unittest.TestCase):
    def test_http_probe_uses_head_without_body_or_redirect(self):
        calls = []
        class Connection:
            def __init__(self, host, timeout):
                calls.append((host, timeout))
            def request(self, method, path, headers):
                calls.append((method, path, headers["User-Agent"]))
            def getresponse(self):
                return SimpleNamespace(status=302)
            def close(self):
                calls.append("closed")
        result = http_probe("example.com", connection_factory=Connection)
        self.assertEqual(result["http_status"], 302)
        self.assertEqual(calls[1][:2], ("HEAD", "/"))
        self.assertEqual(calls[-1], "closed")
        with self.assertRaises(ValueError):
            http_probe("example.com:443", connection_factory=Connection)

    def test_summary_and_classification_keep_icmp_limits(self):
        result = summarize([10.0, None, 20.0, 30.0])
        self.assertEqual(result["packet_loss_percent"], 25)
        self.assertEqual(result["jitter_ms"], 10)
        self.assertIn("możliwy", classify(result, result, True)["category"])

    def test_ping_and_mtu_with_fixture_runner(self):
        def runner(command, **kwargs):
            if "-l" in command:
                payload = int(command[command.index("-l") + 1])
                return SimpleNamespace(returncode=0 if payload + 28 <= 1400 else 1, stdout="")
            return SimpleNamespace(returncode=0, stdout="Reply: time=12.5ms")
        self.assertEqual(ping_sample("192.0.2.1", runner=runner, platform="nt"), 12.5)
        self.assertEqual(mtu_probe("192.0.2.1", runner=runner, platform="nt")["estimated_ipv4_mtu"], 1400)

    def test_diagnose_and_validation(self):
        def runner(command, **kwargs):
            if command[0] == "ping":
                return SimpleNamespace(returncode=0, stdout="Reply: time=8ms")
            return SimpleNamespace(returncode=0, stdout="")
        result = diagnose("192.0.2.1", gateway="192.0.2.254", count=2,
                          runner=runner, platform="nt")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["internet"]["received"], 2)
        self.assertTrue(result["dns"]["ok"])
        with self.assertRaises(ValueError):
            diagnose("not-an-ip", runner=runner)
