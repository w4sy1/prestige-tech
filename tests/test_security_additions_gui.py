import os
import unittest
from unittest.mock import patch


class SecurityAdditionsGuiTests(unittest.TestCase):
    def test_virustotal_requires_confirmation_before_worker(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
        from prestige_security.gui import SecurityCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SecurityCenterWindow()
        with patch.object(QFileDialog, "getOpenFileName", return_value=("C:/sample.exe", "")), \
             patch.object(QMessageBox, "question", return_value=QMessageBox.No), \
             patch.object(window, "_start") as start:
            window.choose_virustotal()
            start.assert_not_called()
        window.close()

    def test_optimization_result_is_read_only_in_gui(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_system.gui import SystemCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SystemCenterWindow()
        window.show_result({"action": "optimization", "diagnostic": {
            "read_only": True, "findings": [], "sections": {}}})
        self.assertIn("Audyt bez zmian", window.status.text())
        window.close()


if __name__ == "__main__":
    unittest.main()
