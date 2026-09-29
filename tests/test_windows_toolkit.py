import json
import os
import unittest
from types import SimpleNamespace

from prestige_core.windows_toolkit import QUERIES, collect


class WindowsToolkitTests(unittest.TestCase):
    def test_bounded_read_only_sections(self):
        seen = []

        def runner(command, **kwargs):
            seen.append((command, kwargs))
            sections = {name: {"status": "OK", "data": []} for name in QUERIES}
            sections["reboot"]["data"] = [{"CBS": False, "WindowsUpdate": True}]
            sections["update_history"] = {"status": "UNKNOWN", "data": [], "error": "COMException"}
            return SimpleNamespace(returncode=0, stdout=json.dumps(sections))

        result = collect(runner=runner, platform="nt")
        self.assertEqual(len(result["sections"]), 14)
        self.assertIn("available_updates", result["sections"])
        self.assertIn("smart", result["sections"])
        self.assertIn("run_registry", result["sections"])
        self.assertIn("events", result["sections"])
        self.assertEqual(result["sections"]["update_history"]["status"], "UNKNOWN")
        self.assertEqual(result["sections"]["reboot"]["data"][0]["WindowsUpdate"], True)
        self.assertEqual(seen[0][1]["timeout"], 180)
        self.assertIn("-EncodedCommand", seen[0][0])

    def test_invalid_data_and_non_windows_are_rejected(self):
        def runner(*_args, **_kwargs):
            return SimpleNamespace(returncode=0, stdout=json.dumps({
                name: {"status": "OK", "data": {}} for name in QUERIES}))

        with self.assertRaises(RuntimeError):
            collect(runner=runner, platform="nt")
        with self.assertRaises(RuntimeError):
            collect(platform="posix")


class WindowsToolkitGuiTests(unittest.TestCase):
    def test_diagnostic_control_exists(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_system.gui import SystemCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SystemCenterWindow()
        self.assertTrue(window.toolkit_button.isEnabled())
        window.close()
