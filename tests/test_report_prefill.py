import os
import unittest

from prestige_core.report_prefill import summarize_center_result


class ReportPrefillTests(unittest.TestCase):
    def test_system_counts_without_private_paths(self):
        result = {"action": "capture", "path": "C:/Private/secret.json", "unknown": 2}
        summary = summarize_center_result("System", "capture", result)
        self.assertIn("2", summary["diagnoza"])
        self.assertNotIn("Private", str(summary))
        self.assertNotIn("test_koncowy", summary)

    def test_security_summary_does_not_copy_evidence(self):
        result = {"data": {"risk_score": 42, "unknown_checks": 3,
                           "evidence": {"path": "C:/Private/secret"}}}
        summary = summarize_center_result("Security", "audit", result)
        self.assertIn("42/100", summary["diagnoza"])
        self.assertNotIn("secret", str(summary))

    def test_report_dialog_prefills_only_verified_fields(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_report.gui import ReportDialog
        app = QApplication.instance() or QApplication([])
        dialog = ReportDialog(prefill={"diagnoza": "Dwie sekcje UNKNOWN.",
                                       "wykonane_czynnosci": "Odczyt.",
                                       "klient": "Nie kopiuj"})
        self.assertEqual(dialog.fields["diagnoza"].toPlainText(), "Dwie sekcje UNKNOWN.")
        self.assertEqual(dialog.fields["klient"].text(), "")
        self.assertEqual(dialog.fields["test_koncowy"].toPlainText(), "")
        dialog.close()


if __name__ == "__main__":
    unittest.main()
