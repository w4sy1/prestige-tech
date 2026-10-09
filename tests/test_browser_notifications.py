import json
import os
from pathlib import Path
import tempfile
import unittest

from prestige_core.browser_notifications import collect_notification_permissions


class BrowserNotificationTests(unittest.TestCase):
    def test_reads_only_allowed_domains_without_private_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / "Google" / "Chrome" / "User Data" / "Default"
            profile.mkdir(parents=True)
            (profile / "Preferences").write_text(json.dumps({"profile": {"content_settings": {
                "exceptions": {"notifications": {
                    "https://alerts.example:443,*": {"setting": 1},
                    "https://blocked.example:443,*": {"setting": 2},
                    "https://private.example/path?token=secret,*": {"setting": 1},
                }}}}}), encoding="utf-8")
            result = collect_notification_permissions(local_app_data=folder)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual([row["domain"] for row in result["allowed_sites"]],
                             ["alerts.example", "private.example"])
            self.assertNotIn("secret", str(result))
            self.assertFalse(result["system_changed"])

    def test_corrupt_profile_is_unknown_not_empty_ok(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / "Microsoft" / "Edge" / "User Data" / "Default"
            profile.mkdir(parents=True)
            (profile / "Preferences").write_text("{", encoding="utf-8")
            result = collect_notification_permissions(local_app_data=folder)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["errors"], 1)
            (profile / "Preferences").write_text('{"profile":"wrong"}', encoding="utf-8")
            result = collect_notification_permissions(local_app_data=folder)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["errors"], 1)

    def test_security_gui_does_not_change_permissions(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_security.gui import SecurityCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SecurityCenterWindow()
        try:
            window.show_result({"action": "notifications", "data": {
                "status": "COMPLETE", "profiles_read": 1, "errors": 0,
                "allowed_sites": [{"domain": "alerts.example", "browser": "Edge",
                                   "profile": "Default", "permission": "ALLOW"}],
                "system_changed": False}})
            self.assertIn("alerts.example", window.result.toPlainText())
            self.assertIn("Ustawienia zmień w przeglądarce", window.status.text())
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
