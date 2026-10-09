import os
import unittest
from unittest.mock import patch


class SystemHelpGuiTests(unittest.TestCase):
    def test_disk_problem_shows_real_measurement_without_cleanup(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_system.gui import SystemCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SystemCenterWindow()
        try:
            with patch("prestige_system.gui.check_disk_space", return_value={
                    "free_percent": 12.5, "free_bytes": 125000000}) as check, \
                    patch.object(window, "start_cleanup_scan") as cleanup:
                window.show_problem_plan()
                check.assert_called_once_with()
                cleanup.assert_not_called()
            self.assertIn("12.5%", window.result.toPlainText())
            self.assertIn("bez usuwania plików", window.status.text())
        finally:
            window.close()

    def test_audio_problem_does_not_claim_diagnosis(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_system.gui import SystemCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SystemCenterWindow()
        try:
            window.problem_choice.setCurrentIndex(1)
            window.show_problem_plan()
            self.assertIn("Automatyczny pomiar tego problemu nie jest jeszcze dostępny",
                          window.result.toPlainText())
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
