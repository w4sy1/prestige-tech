import os
import unittest
from unittest.mock import patch

from prestige_core.report_live import summarize_live_result


class ReportLiveTests(unittest.TestCase):
    def test_summaries_omit_private_source_values_and_diagnosis(self):
        samples = (
            ("Android", {"serial": "PRIVATE", "status": "UNKNOWN", "truncated": True,
                         "apps": [{"package": "private.app", "permissions": "secret"}]}),
            ("Termux", {"status": "UNAVAILABLE", "termux_detected": False,
                        "commands": {"pkg": False}, "home": "C:/Secret"}),
            ("AI", {"mode": "LOCAL MODE", "data_leaves_device": False,
                    "alerts": [{"source": "secret"}]}),
            ("AI", {"mode": "EXTERNAL AI", "data_leaves_device": True,
                    "analysis": "secret"}),
            ("Network", {"status": "UNKNOWN", "probed": 2, "responsive": [{"ip": "private"}],
                         "observed": [{"evidence": "Cache — dostępność nieznana", "name": "secret"}]}),
            ("Monitor", {"schema_version": 1, "root": "C:/Private",
                         "events": [{"at_utc": "2026-10-08T10:00:00Z", "path": "secret.txt",
                                     "kind": "Nowy"}]}),
            ("Registry", {"status": "CANCELLED", "total": 500, "processed": 4,
                          "counts": {"ERROR": 1}, "errors": [{"operation": "secret"}]}),
            ("Storage", {"copied": 2, "ok": False, "errors": ["C:/Secret"],
                         "destination": "C:/Private", "vss_cleanup_required": True}),
        )
        for center, result in samples:
            summary = summarize_live_result(center, result)
            self.assertEqual(set(summary), {"wykonane_czynnosci"})
            self.assertNotIn("private", str(summary).lower())
            self.assertNotIn("secret", str(summary).lower())
        with self.assertRaises(ValueError):
            summarize_live_result("Android", {"apps": [], "status": "INVALID"})

    def test_three_windows_open_report_without_diagnosis(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_android.gui import AndroidCenterWindow
        from prestige_termux.gui import TermuxCenterWindow
        from prestige_ai.gui import AiDialog

        app = QApplication.instance() or QApplication([])
        android = AndroidCenterWindow(autoload=False)
        android.device_choice.addItem("device", "SERIAL")
        android.apps_snapshot = {"serial": "SERIAL", "status": "COMPLETE", "apps": []}
        with patch("prestige_android.gui.ReportDialog") as dialog:
            android.open_report()
            self.assertEqual(set(dialog.call_args.kwargs["prefill"]), {"wykonane_czynnosci"})
        android.close()

        termux = TermuxCenterWindow()
        termux.last_health = {"status": "READY", "termux_detected": True,
                              "commands": {"pkg": True}}
        with patch("prestige_termux.gui.ReportDialog") as dialog:
            termux.open_report()
            self.assertEqual(set(dialog.call_args.kwargs["prefill"]), {"wykonane_czynnosci"})
        termux.close()

        ai = AiDialog()
        ai.last_result = {"mode": "LOCAL MODE", "data_leaves_device": False, "alerts": []}
        with patch("prestige_ai.gui.ReportDialog") as dialog:
            ai.open_report()
            self.assertEqual(set(dialog.call_args.kwargs["prefill"]), {"wykonane_czynnosci"})
        ai.close()

        from prestige_network_center.gui import NetworkCenterWindow
        from prestige_monitor.gui import MonitorWindow
        network = NetworkCenterWindow(autoload=False)
        network.last_discovery_result = {"status": "COMPLETE", "probed": 1,
                                         "responsive": [], "observed": []}
        with patch("prestige_network_center.gui.ReportDialog") as dialog:
            network.open_discovery_report()
            self.assertEqual(set(dialog.call_args.kwargs["prefill"]), {"wykonane_czynnosci"})
        network.close()

        monitor = MonitorWindow()
        monitor.history = {"schema_version": 1, "root": "C:/Data",
                           "events": [{"at_utc": "2026-10-08T10:00:00Z",
                                       "path": "file.txt", "kind": "Nowy"}]}
        with patch("prestige_monitor.gui.ReportDialog") as dialog:
            monitor.open_history_report()
            self.assertEqual(set(dialog.call_args.kwargs["prefill"]), {"wykonane_czynnosci"})
        monitor.close()

        from prestige_registry.gui import RegistryWindow
        registry = RegistryWindow()
        registry.last_audit = {"status": "COMPLETE", "total": 1,
                               "processed": 1, "counts": {"OK": 1}, "errors": []}
        with patch("prestige_registry.gui.ReportDialog") as dialog:
            registry.open_audit_report()
            self.assertEqual(set(dialog.call_args.kwargs["prefill"]), {"wykonane_czynnosci"})
        registry.close()

        from prestige_storage.gui import StorageWindow
        storage = StorageWindow(autoload=False)
        storage.last_backup_result = {"copied": 2, "ok": True, "errors": []}
        storage.active_backup_operation = "backup"
        storage.show_usb_result({"ok": True, "updated": 1})
        self.assertEqual(storage.last_backup_result["copied"], 2)
        with patch("prestige_storage.gui.ReportDialog") as dialog:
            storage.open_backup_report()
            self.assertEqual(set(dialog.call_args.kwargs["prefill"]), {"wykonane_czynnosci"})
        storage.close()


if __name__ == "__main__":
    unittest.main()
