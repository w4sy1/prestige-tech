from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from prestige_core.sentinel_status import read_sentinel_events, read_sentinel_status


class SentinelStatusTests(unittest.TestCase):
    def test_reads_fresh_status_without_claiming_process_is_alive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sentinel-status.json"
            now = datetime.now(timezone.utc)
            path.write_text(json.dumps({
                "module": "network-sentinel", "bridgeVersion": 2,
                "version": "2.0.0", "running": True, "admin": False,
                "deepCapture": False, "onlineDevices": 3, "newDevices": 1,
                "threats": 0, "alertCount": 2, "timestamp": now.isoformat(),
            }), encoding="utf-8")
            result = read_sentinel_status(path, now=now)
            self.assertFalse(result["stale"])
            self.assertTrue(result["running_reported"])
            self.assertEqual(result["online_devices"], 3)
            self.assertTrue(path.exists())

    def test_old_report_is_stale_even_when_running_flag_is_true(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "status.json"
            now = datetime.now(timezone.utc)
            path.write_text(json.dumps({
                "module": "network-sentinel", "bridgeVersion": 2,
                "running": True, "admin": False, "deepCapture": False,
                "onlineDevices": 0, "newDevices": 0, "threats": 0,
                "alertCount": 0, "timestamp": (now - timedelta(minutes=5)).isoformat(),
            }), encoding="utf-8")
            self.assertTrue(read_sentinel_status(path, now=now)["stale"])

    def test_rejects_unrelated_or_invalid_bridge(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "status.json"
            path.write_text('{"module":"other","bridgeVersion":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_sentinel_status(path)

    def test_reads_recent_events_and_marks_corrupt_line_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text(
                '{"Time":"2026-09-27 10:00:00","Severity":"HIGH","Type":"Port sweep","SourceIP":"192.0.2.2"}\n'
                '{bad json}\n', encoding="utf-8")
            result = read_sentinel_events(path)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["malformed"], 1)
            self.assertEqual(result["events"][0]["type"], "Port sweep")


if __name__ == "__main__":
    unittest.main()
