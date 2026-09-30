import os
import tempfile
import unittest
from unittest.mock import patch


class NetworkGuiTests(unittest.TestCase):
    def test_lan_history_toggle_does_not_close_dns_history(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_network_center.gui import NetworkCenterWindow
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"LOCALAPPDATA": directory}):
            window = NetworkCenterWindow(autoload=False)
            window.toggle_dns_history()
            self.assertIsNotNone(window.dns_history)
            window.toggle_local_history()
            self.assertIsNotNone(window.device_history)
            window.toggle_local_history()
            self.assertIsNone(window.device_history)
            self.assertIsNotNone(window.dns_history)
            window.close()

    def test_lan_json_import_requires_confirmation_for_complete_observation(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_network_center.gui import NetworkCenterWindow
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"LOCALAPPDATA": directory}):
            source = os.path.join(directory, "observed.json")
            with open(source, "w", encoding="utf-8") as stream:
                stream.write('[{"mac":"00:11:22:33:44:55","ip":"192.0.2.5"}]')
            window = NetworkCenterWindow(autoload=False)
            window.toggle_local_history()
            with patch("prestige_network_center.gui.QFileDialog.getOpenFileName", return_value=(source, "")), \
                    patch("prestige_network_center.gui.QMessageBox.question", return_value=QMessageBox.No):
                window.import_lan_observation()
            self.assertEqual(window.device_history.devices()[0]["status"], "observed")
            with open(source, "w", encoding="utf-8") as stream:
                stream.write("[]")
            with patch("prestige_network_center.gui.QFileDialog.getOpenFileName", return_value=(source, "")), \
                    patch("prestige_network_center.gui.QMessageBox.question", return_value=QMessageBox.Yes):
                window.import_lan_observation()
            self.assertEqual(window.device_history.devices()[0]["status"], "not_observed")
            window.close()

    def test_discovery_result_then_error_clears_stale_rows(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_network_center.gui import NetworkCenterWindow
        application = QApplication.instance() or QApplication([])
        window = NetworkCenterWindow(autoload=False)
        window.show_discovery({"responsive": [{"ip": "192.168.1.3", "mac": None}],
                               "status": "COMPLETE", "scope": "192.168.1.0/24",
                               "probed": 253, "note": "Brak odpowiedzi nie dowodzi offline."})
        self.assertEqual(window.discovery_table.rowCount(), 1)
        window.show_discovery_error("Brak dostępu")
        self.assertEqual(window.discovery_table.rowCount(), 0)
        self.assertIn("Brak dostępu", window.discovery_note.text())
        window.close()

    def test_display_then_read_error_clears_stale_data(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_core.ui_theme import install_font
        from prestige_network_center.gui import NetworkCenterWindow

        application = QApplication.instance() or QApplication([])
        install_font(application)
        window = NetworkCenterWindow(autoload=False)
        window.show_neighbors([{
            "ips": ["10.0.0.2"], "mac": "a0:b1:c2:d3:e4:f5",
            "states": ["Reachable"], "interfaces": ["7"],
        }])
        self.assertEqual(window.table.rowCount(), 1)
        self.assertEqual(window.table.item(0, 0).text(), "10.0.0.2")
        window.show_error("Brak polecenia systemowego")
        self.assertEqual(window.table.rowCount(), 0)
        self.assertEqual(window.count.text(), "Dane niedostępne")
        self.assertIn("Brak polecenia", window.status.text())
        window.show_adapters([{
            "name": "Ethernet", "ipv4": ["192.0.2.4"],
            "gateway": ["192.0.2.1"], "dns": ["9.9.9.9"],
        }])
        self.assertEqual(window.adapter_table.rowCount(), 1)
        window.show_adapter_error("Brak danych")
        self.assertEqual(window.adapter_table.rowCount(), 0)
        self.assertIn("Brak danych", window.adapter_status.text())
        window.show_sentinel_status({
            "stale": True, "timestamp": "2026-09-27T10:00:00+00:00",
            "running_reported": True, "online_devices": 2, "new_devices": 1,
            "threats": 0, "alert_count": 3, "interface": "Ethernet",
            "ip": "192.0.2.4", "gateway": "192.0.2.1",
        })
        self.assertIn("NIEAKTUALNY", window.sentinel_status.text())
        window.show_sentinel_events({"status": "UNKNOWN", "events": [{
            "time": "2026-09-27 10:00:00", "severity": "HIGH",
            "type": "Port sweep", "source_ip": "192.0.2.2",
        }]})
        self.assertEqual(window.sentinel_events_table.rowCount(), 1)
        self.assertIn("UNKNOWN", window.sentinel_events_note.text())
        window.close()


if __name__ == "__main__":
    unittest.main()
