from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prestige_core.family_summary import build_family_summary, render_family_text, save_family_text


class FamilySummaryTests(unittest.TestCase):
    def test_summary_includes_only_checked_fields_and_never_claims_sent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prestige-check-example.json"
            path.write_text(json.dumps({"schema_version": 1, "created_utc": "2026-10-09T10:00:00+00:00",
                                        "checks": {"disk": {"status": "COMPLETE", "free_percent": 20,
                                                            "secret_path": "private"}}}), encoding="utf-8")
            result = build_family_summary(folder, now=datetime(2026, 10, 9, 12, tzinfo=timezone.utc))
            text = render_family_text(result)
            self.assertIn("20% wolnego", text)
            self.assertIn("Internet: nie sprawdzono", text)
            self.assertNotIn("private", text)
            self.assertFalse(result["sent"])
            output = Path(folder) / "stan.txt"
            save_family_text(result, output)
            with self.assertRaises(FileExistsError):
                save_family_text(result, output)

    def test_report_gui_requires_preview_before_saving(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_report.gui import ReportDialog
        app = QApplication.instance() or QApplication([])
        dialog = ReportDialog()
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "prestige-check-example.json"
                path.write_text(json.dumps({"schema_version": 1,
                                            "created_utc": datetime.now(timezone.utc).isoformat(),
                                            "checks": {"disk": {"status": "COMPLETE",
                                                                "free_percent": 25}}}), encoding="utf-8")
                with patch("prestige_report.gui.QFileDialog.getExistingDirectory", return_value=folder), \
                        patch("prestige_report.gui.QMessageBox.question", return_value=QMessageBox.No), \
                        patch("prestige_report.gui.QFileDialog.getSaveFileName") as save:
                    dialog.create_family_summary()
                    save.assert_not_called()
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
