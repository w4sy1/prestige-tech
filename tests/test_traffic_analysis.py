import json
import tempfile
from pathlib import Path
import unittest

from prestige_core.traffic_analysis import analyze_log, detect_attempts, parse_log


class TrafficAnalysisTests(unittest.TestCase):
    def test_detects_port_pattern_and_respects_whitelist(self):
        lines = [json.dumps({"timestamp": f"2026-09-27T10:00:{second:02d}+00:00",
                             "src": "192.0.2.10", "dst": "192.0.2.20", "port": 1000 + second,
                             "protocol": "TCP", "syn": True}) for second in range(10)]
        events, rejected = parse_log("\n".join(lines), "jsonl")
        self.assertEqual(rejected, 0)
        self.assertEqual(len(detect_attempts(events, ["192.0.2.20"])["alerts"]), 1)
        self.assertEqual(detect_attempts(events, ["192.0.2.20"],
                                         whitelist=["192.0.2.0/24"])["alerts"], [])

    def test_windows_log_and_invalid_row_are_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pfirewall.log"
            path.write_text("#Fields: date time src-ip dst-ip dst-port protocol tcpflags\n"
                            "2026-09-27 10:00:00 192.0.2.10 192.0.2.20 80 TCP S\n"
                            "broken\n", encoding="utf-8")
            result = analyze_log(path, "windows", ["192.0.2.20"], utc_offset="+02:00")
            self.assertEqual(result["records"], 1)
            self.assertEqual(result["rejected"], 1)
            self.assertEqual(result["status"], "UNKNOWN")
