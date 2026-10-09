import os
import unittest
from unittest.mock import patch


class NetworkScheduleTest(unittest.TestCase):
    def test_schedule_requires_selected_scope_and_has_session_limit(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_network_center.gui import NetworkCenterWindow
        app = QApplication.instance() or QApplication([])
        window = NetworkCenterWindow(autoload=False)
        window.start_discovery_schedule()
        self.assertFalse(window.discovery_timer.isActive())
        window.last_discovery_scope = {"scope": "192.168.1.0/24", "ip": "192.168.1.2",
                                       "index": 3, "interface": "Fixture"}
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            window.start_discovery_schedule()
        self.assertTrue(window.discovery_timer.isActive())
        self.assertEqual(window.scheduled_remaining, 3)
        self.assertEqual(window.discovery_timer.interval(), 30 * 60 * 1000)
        window.stop_discovery_schedule()
        self.assertFalse(window.discovery_timer.isActive())
        window.close()


if __name__ == "__main__":
    unittest.main()
