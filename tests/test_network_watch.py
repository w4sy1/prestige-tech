import base64
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from prestige_core.network_watch import make_profile, read_event_history, run_watch, save_profile
from prestige_core.network_watch_schedule import install, schedule_plan
from prestige_core.port_guidance import explain_hosts


class NetworkWatchTests(unittest.TestCase):
    def test_baseline_then_new_device_without_claiming_attack(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = make_profile("192.168.1.0/24", "192.168.1.10", 4)
            save_profile(profile, directory)
            scopes = lambda: [{"scope": profile["scope"], "ip": profile["local_ip"],
                               "index": profile["interface_index"]}]
            first = lambda *_args, **_kwargs: {
                "status": "COMPLETE", "cancelled": False, "probe_errors": 0,
                "observed": [{"ip": "192.168.1.1", "mac": "aa:bb:cc:dd:ee:ff",
                              "evidence": "ICMP"}]}
            initial = run_watch(directory, scopes_reader=scopes, scanner=first,
                                now=datetime(2026, 10, 9, tzinfo=timezone.utc))
            self.assertEqual(initial["events"], [])
            second = lambda *_args, **_kwargs: {
                "status": "COMPLETE", "cancelled": False, "probe_errors": 0,
                "observed": [{"ip": "192.168.1.1", "mac": "aa:bb:cc:dd:ee:ff",
                              "evidence": "ICMP"},
                             {"ip": "192.168.1.20", "mac": "", "evidence": "ICMP"}]}
            result = run_watch(directory, scopes_reader=scopes, scanner=second)
            self.assertEqual(result["events"][0]["type"], "NEW_OBSERVATION")
            self.assertFalse(result["system_changed"])
            self.assertNotIn("atak", result["events"][0]["note"].lower())
            self.assertEqual(read_event_history(directory)[0]["type"], "NEW_OBSERVATION")

    def test_network_change_skips_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            save_profile(make_profile("192.168.1.0/24", "192.168.1.10", 4), directory)
            result = run_watch(directory, scopes_reader=lambda: [],
                               scanner=lambda *_args, **_kwargs: self.fail("scan"))
            self.assertEqual(result["status"], "SKIPPED")
            self.assertFalse((Path(directory) / "last-complete.json").exists())

    def test_partial_scan_keeps_previous_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = make_profile("192.168.1.0/24", "192.168.1.10", 4)
            save_profile(profile, directory)
            scope = lambda: [{"scope": profile["scope"], "ip": profile["local_ip"],
                              "index": profile["interface_index"]}]
            good = lambda *_args, **_kwargs: {"status": "COMPLETE", "observed": [],
                                             "cancelled": False}
            run_watch(directory, scopes_reader=scope, scanner=good)
            baseline = (Path(directory) / "last-complete.json").read_bytes()
            partial = lambda *_args, **_kwargs: {"status": "UNKNOWN", "observed": [
                {"ip": "192.168.1.20", "evidence": "ICMP"}], "probe_errors": 1}
            result = run_watch(directory, scopes_reader=scope, scanner=partial)
            self.assertEqual(result["status"], "PARTIAL")
            self.assertEqual(result["events"], [])
            self.assertEqual((Path(directory) / "last-complete.json").read_bytes(), baseline)

    def test_schedule_is_non_admin_and_never_auto_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            save_profile(make_profile("192.168.1.0/24", "192.168.1.10", 4), directory)
            plan = schedule_plan(directory)
            self.assertFalse(plan["automatic_blocking"])
            calls = []
            def runner(command, **_kwargs):
                calls.append(command)
                return SimpleNamespace(returncode=0)
            install(plan, runner=runner, platform="nt")
            script = base64.b64decode(calls[0][-1]).decode("utf-16le")
            self.assertIn("-LogonType Interactive -RunLevel Limited", script)
            self.assertIn("prestige_core.network_watch", script)
            plan["arguments"] += " --extra"
            with self.assertRaises(ValueError):
                install(plan, runner=runner, platform="nt")
            self.assertEqual(len(calls), 1)

    def test_port_guidance_is_observation_not_attack_verdict(self):
        result = explain_hosts({"192.168.1.1": {"ports": {
            "tcp/23": {"state": "open"}, "tcp/80": {"state": "filtered"}}}})
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["port"], "tcp/23")
        self.assertEqual(result["findings"][0]["certainty"], "OBSERVATION")


if __name__ == "__main__":
    unittest.main()
