import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class RegistryManagedGuiTests(unittest.TestCase):
    def test_apply_uses_automatic_backup_path_without_save_dialog(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_registry.gui import RegistryWindow

        app = QApplication.instance() or QApplication([])
        with patch("prestige_registry.gui.list_backups", return_value=[]):
            window = RegistryWindow()
        try:
            with tempfile.TemporaryDirectory() as directory:
                backup = Path(directory) / "automatic.json"
                with (patch("prestige_registry.gui.QMessageBox.question", return_value=QMessageBox.Yes),
                      patch("prestige_registry.gui.new_backup_path", return_value=backup),
                      patch("prestige_registry.gui.show_file_extensions",
                            return_value={"status": "APPLIED", "backup": str(backup)}) as apply,
                      patch("prestige_registry.gui.QFileDialog.getSaveFileName") as save_dialog,
                      patch("prestige_registry.gui.list_backups", return_value=[])):
                    window.apply_extensions_change()
                    apply.assert_called_once_with(backup, accept_changes=True)
                    save_dialog.assert_not_called()
                    self.assertIn("Jak cofnąć:", window.change_summary.text())
        finally:
            window.close()

    def test_managed_rollback_previews_and_confirms(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_registry.gui import RegistryWindow

        app = QApplication.instance() or QApplication([])
        with patch("prestige_registry.gui.list_backups", return_value=[]):
            window = RegistryWindow()
        try:
            item = {"operation": "REG-WRITE-002", "label": "Pokaż pliki ukryte",
                    "kind": "change", "status": "APPLIED", "path": "C:/backup.json"}
            window.backups_choice.addItem("Ostatnia zmiana", item)
            with (patch("prestige_registry.gui.preview_rollback_change",
                        return_value={"status": "PLAN"}) as preview,
                  patch("prestige_registry.gui.QMessageBox.question", return_value=QMessageBox.Yes),
                  patch("prestige_registry.gui.rollback_change",
                        return_value={"status": "ROLLED_BACK"}) as rollback,
                  patch("prestige_registry.gui.list_backups", return_value=[])):
                window.rollback_managed_backup()
                preview.assert_called_once_with("C:/backup.json")
                rollback.assert_called_once_with("C:/backup.json", accept_changes=True)
        finally:
            window.close()

    def test_incomplete_backup_needs_manual_review(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_registry.gui import RegistryWindow

        app = QApplication.instance() or QApplication([])
        with patch("prestige_registry.gui.list_backups", return_value=[]):
            window = RegistryWindow()
        try:
            window.backups_choice.addItem("Niepełna kopia", {
                "operation": "REG-WRITE-002", "kind": "change",
                "status": "RECOVERY_NEEDED", "path": "C:/backup.json",
            })
            self.assertFalse(window.managed_rollback_button.isEnabled())
            self.assertIn("ręcznej kontroli", window.backup_note.text())
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
