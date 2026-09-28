import os
import unittest


class AndroidGuiTest(unittest.TestCase):
    def test_device_list_and_error_clear_stale_rows(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_android.gui import AndroidCenterWindow
        app = QApplication.instance() or QApplication([])
        window = AndroidCenterWindow(autoload=False)
        window._show("devices", [{"serial": "TEST1", "state": "device", "authorized": True},
                                 {"serial": "TEST2", "state": "unauthorized", "authorized": False}])
        self.assertEqual(window.device_choice.count(), 1)
        window._show("apps", {"apps": [{"package": "com.example.app", "version": "1",
                                         "interest": "NORMAL", "special_indicators": []}],
                              "status": "COMPLETE", "truncated": False})
        self.assertEqual(window.apps_table.rowCount(), 1)
        window._error("apps", "ADB brak")
        self.assertEqual(window.apps_table.rowCount(), 0)
        self.assertIn("ADB brak", window.status.text())
        window.close()
