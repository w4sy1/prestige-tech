import os
import tempfile
import unittest
from unittest.mock import patch


class NetworkWatchGuiTests(unittest.TestCase):
    def test_profile_and_schedule_require_explicit_confirmation(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_network_center.gui import NetworkCenterWindow
        app = QApplication.instance() or QApplication([])
        window = NetworkCenterWindow(autoload=False)
        with tempfile.TemporaryDirectory() as folder:
            from prestige_core.network_watch_schedule import schedule_plan
            window.last_discovery_scope = {"scope": "192.168.1.0/24",
                                           "ip": "192.168.1.10", "index": 3}
            with patch("prestige_network_center.gui.network_watch_directory", return_value=folder), \
                 patch("prestige_network_center.gui.network_watch_schedule_plan",
                       side_effect=lambda: schedule_plan(folder)):
                window.save_network_watch_profile()
                with patch.object(QMessageBox, "question", return_value=QMessageBox.No), \
                     patch("prestige_network_center.gui.install_network_watch") as install:
                    window.install_network_watch_schedule()
                    install.assert_not_called()
                with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
                     patch("prestige_network_center.gui.install_network_watch") as install:
                    window.install_network_watch_schedule()
                    install.assert_called_once()
        window.close()


if __name__ == "__main__":
    unittest.main()
