import base64
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from prestige_core.daily_schedule import install_daily_schedule, schedule_plan


class DailyScheduleTests(unittest.TestCase):
    def test_plan_is_read_only_and_internet_opt_in(self):
        with tempfile.TemporaryDirectory() as folder:
            plan = schedule_plan("02:30", report_dir=folder)
        self.assertFalse(plan["automatic_repairs"])
        self.assertTrue(plan["requires_logged_in_user"])
        self.assertNotIn("--internet", plan["arguments"])
        with self.assertRaises(ValueError):
            schedule_plan("24:00")

    def test_install_builds_limited_interactive_task_without_running_real_powershell(self):
        calls = []

        def fake_runner(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as folder:
            plan = schedule_plan("03:15", report_dir=Path(folder) / "O'Brien",
                                 include_internet=True)
            result = install_daily_schedule(plan, runner=fake_runner, platform="nt")
        self.assertEqual(result["status"], "REGISTERED")
        self.assertEqual(len(calls), 1)
        command = calls[0][0]
        script = base64.b64decode(command[-1]).decode("utf-16le")
        self.assertIn("-LogonType Interactive -RunLevel Limited", script)
        self.assertIn("-ExecutionTimeLimit (New-TimeSpan -Minutes 5)", script)
        self.assertIn("O''Brien", script)
        self.assertIn("--internet", script)
        self.assertNotIn("-RunLevel Highest", script)

    def test_tampered_plan_is_rejected_before_runner(self):
        plan = schedule_plan()
        plan["arguments"] += " --unexpected"
        with self.assertRaises(ValueError):
            install_daily_schedule(plan, runner=lambda *_args, **_kwargs: self.fail("runner"),
                                   platform="nt")


if __name__ == "__main__":
    unittest.main()
