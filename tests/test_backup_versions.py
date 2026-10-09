import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prestige_core.backup import backup
from prestige_core.backup.versions import list_versions


class BackupVersionsTests(unittest.TestCase):
    def test_lists_real_backup_without_claiming_integrity_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "Documents"
            source.mkdir()
            (source / "letter.txt").write_text("sample", encoding="utf-8")
            destination = root / "Copies" / "yesterday"
            backup([source], destination)
            overview = list_versions(destination.parent)
            self.assertEqual(overview["total_found"], 1)
            self.assertEqual(overview["versions"][0]["file_count"], 1)
            self.assertTrue(overview["versions"][0]["complete"])
            self.assertFalse(overview["versions"][0]["integrity_checked"])

    def test_storage_gui_shows_versions_without_restoring(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_storage.gui import StorageWindow
        app = QApplication.instance() or QApplication([])
        window = StorageWindow(autoload=False)
        try:
            with patch("prestige_storage.gui.QFileDialog.getExistingDirectory", return_value="C:/Copies"), \
                    patch("prestige_storage.gui.list_versions", return_value={
                        "versions": [{"name": "copy-1", "file_count": 2, "complete": True,
                                      "modified_utc": "2026-10-09T10:00:00+00:00"}],
                        "total_found": 1, "unreadable": 0, "note": "Sprawdź kopię."}), \
                    patch("prestige_storage.gui.QMessageBox.information") as notice, \
                    patch.object(window, "_run_backup_operation") as operation:
                window.show_backup_versions()
                notice.assert_called_once()
                operation.assert_not_called()
            self.assertIn("Wersje: 1", window.status.text())
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
