import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.traffic_stream import RollingDetector, TrafficStream


class TrafficStreamTest(unittest.TestCase):
    def test_partial_line_is_not_lost_or_repeated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.jsonl"
            row = {"timestamp": "2026-09-27T12:00:00Z", "src": "192.0.2.2",
                   "dst": "192.0.2.3", "port": 22, "protocol": "TCP"}
            path.write_text(json.dumps(row), encoding="utf-8")
            stream = TrafficStream(path, "jsonl", ["192.0.2.3"])
            self.assertEqual(stream.poll()["records"], 0)
            with path.open("a", encoding="utf-8") as target:
                target.write("\n")
            self.assertEqual(stream.poll()["records"], 1)
            self.assertEqual(stream.poll()["records"], 0)

    def test_rotation_restarts_and_reports_unknown_window(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "firewall.log"
            path.write_text("#Fields: date time protocol src-ip dst-ip dst-port tcpflags\n", encoding="utf-8")
            stream = TrafficStream(path, "windows", ["192.0.2.3"])
            stream.poll()
            with path.open("a", encoding="utf-8") as target:
                target.write("2026-09-27 12:00:00 TCP 192.0.2.2 192.0.2.3 22 S\n")
            self.assertEqual(stream.poll()["records"], 1)
            path.write_text("#Fields: date time protocol src-ip dst-ip dst-port tcpflags\n", encoding="utf-8")
            result = stream.poll()
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["rotations"], 1)

    def test_alerts_are_not_repeated_at_each_poll(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.jsonl"
            rows = [{"timestamp": f"2026-09-27T12:00:{i:02d}Z", "src": "192.0.2.2",
                     "dst": "192.0.2.3", "port": 1000 + i, "protocol": "TCP", "syn": True}
                    for i in range(10)]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            stream = TrafficStream(path, "jsonl", ["192.0.2.3"])
            self.assertEqual(len(stream.poll()["alerts"]), 1)
            self.assertEqual(stream.poll()["alerts"], [])

    def test_alert_threshold_spans_multiple_polls(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.jsonl"
            stream = TrafficStream(path, "jsonl", ["192.0.2.3"])
            for i in range(10):
                row = {"timestamp": f"2026-09-27T12:00:{i:02d}Z", "src": "192.0.2.2",
                       "dst": "192.0.2.3", "port": 1000 + i, "protocol": "TCP", "syn": True}
                with path.open("a", encoding="utf-8") as target:
                    target.write(json.dumps(row) + "\n")
                result = stream.poll()
                self.assertEqual(len(result["alerts"]), 1 if i == 9 else 0)

    def test_retransmitted_syn_is_counted_once(self):
        detector = RollingDetector(["192.0.2.3"])
        row = {"epoch": 1, "timestamp": "2026-09-27T12:00:01+00:00", "src": "192.0.2.2",
               "dst": "192.0.2.3", "port": 22, "protocol": "TCP", "syn": True,
               "syn_id": "same-sequence"}
        for _ in range(12):
            self.assertIsNone(detector.process(row))
        self.assertEqual(detector.retransmissions, 11)
        self.assertEqual(len(detector.buckets["192.0.2.2"]), 1)
