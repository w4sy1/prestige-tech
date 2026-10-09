import unittest

from pathlib import Path
from unittest.mock import Mock

from prestige_core.senior_assistant import (available_problems, check_disk_space,
                                            check_internet, help_plan, traffic_light)


class SeniorAssistantTests(unittest.TestCase):
    def test_plans_never_claim_to_have_changed_system(self):
        for problem in available_problems():
            plan = help_plan(problem["id"])
            self.assertEqual(plan["status"], "PLAN")
            self.assertFalse(plan["system_changed"])
            self.assertTrue(plan["steps"])
            self.assertTrue(all(not step["automatic"] for step in plan["steps"]))

    def test_unknown_problem_rejected(self):
        with self.assertRaises(ValueError):
            help_plan("unknown")

    def test_unknown_health_never_green(self):
        self.assertEqual(traffic_light()["color"], "yellow")
        self.assertEqual(traffic_light(checks_complete=True)["color"], "green")
        self.assertEqual(traffic_light(threat_confirmed=True)["color"], "red")

    def test_disk_check_reads_space_without_changing_files(self):
        usage = Mock(total=1000, free=100)
        reader = Mock(return_value=usage)
        result = check_disk_space(Path.home(), disk_usage=reader)
        self.assertEqual(result["indicator"]["color"], "yellow")
        self.assertEqual(result["free_percent"], 10.0)
        self.assertFalse(result["system_changed"])
        reader.assert_called_once()

    def test_internet_check_uses_existing_diagnostics_read_only(self):
        result = {"status": "COMPLETE", "target": "1.1.1.1",
                  "internet": {"received": 3, "samples": 3}, "dns": {"ok": True},
                  "web": {"https": {"status": "RESPONSE", "http_status": 200}},
                  "classification": {"category": "OK"}}
        probe = Mock(return_value=result)
        summary = check_internet(diagnose=probe)
        probe.assert_called_once_with("1.1.1.1", gateway=None, count=3, test_http=True)
        self.assertEqual(summary["indicator"]["color"], "green")
        self.assertFalse(summary["system_changed"])

    def test_ping_without_web_response_is_not_green(self):
        result = {"status": "COMPLETE", "target": "1.1.1.1",
                  "internet": {"received": 3, "samples": 3}, "dns": {"ok": True},
                  "web": {"https": {"status": "UNKNOWN"}},
                  "classification": {"category": "UNKNOWN"}}
        self.assertEqual(check_internet(diagnose=lambda *args, **kwargs: result)
                         ["indicator"]["color"], "yellow")


if __name__ == "__main__":
    unittest.main()
