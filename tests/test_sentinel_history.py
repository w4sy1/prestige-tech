import tempfile
from pathlib import Path
import unittest

from prestige_core.sentinel_history import read_device_history


class SentinelHistoryTests(unittest.TestCase):
    def test_reads_latest_events_and_marks_corrupt_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "device-history.jsonl"
            path.write_text('{"Time":"t1","Key":"AA","IP":"192.168.1.2","Event":"NEW","Details":""}\n'
                            'broken\n'
                            '{"Time":"t2","Key":"BB","IP":"192.168.1.3","Event":"CHANGE"}\n',
                            encoding="utf-8")
            result = read_device_history(path, limit=1)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["invalid_rows"], 1)
            self.assertEqual(result["events"][0]["Key"], "BB")
            self.assertEqual(path.read_text(encoding="utf-8").count("broken"), 1)
