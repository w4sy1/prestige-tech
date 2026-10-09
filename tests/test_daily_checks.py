from datetime import datetime, timezone
import json
import tempfile
import unittest

from prestige_core.daily_checks import run_daily_checks, save_daily_report


class DailyCheckTests(unittest.TestCase):
    def test_report_keeps_only_minimal_fields_and_never_claims_repair(self):
        probes = {
            "disk": lambda: {"status": "COMPLETE", "free_percent": 30.0,
                             "indicator": {"color": "green"}},
            "printer": lambda: {"status": "COMPLETE", "service": "Running",
                                "printers": [{"name": "Private printer", "job_count": 1}]},
        }
        report = run_daily_checks(("disk", "printer"), probes=probes,
                                  now=datetime(2026, 10, 9, tzinfo=timezone.utc))
        self.assertEqual(report["indicator"]["color"], "green")
        self.assertFalse(report["system_changed"])
        self.assertNotIn("Private printer", str(report))
        with tempfile.TemporaryDirectory() as folder:
            path = save_daily_report(report, folder)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["checks"]["printer"]
                             ["printer_count"], 1)

    def test_missing_or_partial_check_is_never_green(self):
        report = run_daily_checks(("audio", "internet"), probes={
            "audio": lambda: {"status": "COMPLETE", "devices": [{"name": "Speaker"}]},
            "internet": lambda: (_ for _ in ()).throw(RuntimeError("private details")),
        })
        self.assertEqual(report["indicator"]["color"], "yellow")
        self.assertEqual(report["checks"]["audio"]["status"], "PARTIAL")
        self.assertNotIn("private details", str(report))

    def test_invalid_selection_rejected(self):
        with self.assertRaises(ValueError):
            run_daily_checks(("disk", "disk"))


if __name__ == "__main__":
    unittest.main()
