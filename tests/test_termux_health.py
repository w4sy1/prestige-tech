import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from prestige_core.termux_health import health_check


class TermuxHealthTest(unittest.TestCase):
    def test_missing_termux_is_unavailable_without_execution(self):
        calls = []
        def which(name):
            calls.append(name)
            return None
        result = health_check(environ={"PREFIX": "", "HOME": ""}, which=which)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(len(calls), 5)

    def test_gui_saves_health_result_to_new_json(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_termux.gui import TermuxCenterWindow
        app = QApplication.instance() or QApplication([])
        window = TermuxCenterWindow()
        result = {"status": "UNAVAILABLE", "termux_detected": False,
                  "commands": {"pkg": False}}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "health.json"
            with patch("prestige_termux.gui.health_check", return_value=result), patch(
                    "prestige_termux.gui.QFileDialog.getSaveFileName",
                    return_value=(str(target), "")):
                window.show_health()
                self.assertTrue(window.save_health_button.isEnabled())
                window.save_health()
                window.save_health()
                self.assertIn("Nie zapisano", window.status.text())
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), result)
        window.close()


if __name__ == "__main__":
    unittest.main()
