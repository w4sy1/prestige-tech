import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


class StorageGuiTests(unittest.TestCase):
    def test_usb_prepare_rejects_invalid_plan_before_confirmation(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_storage.gui import StorageWindow
        application = QApplication.instance() or QApplication([])
        window = StorageWindow(autoload=False)
        with patch.object(window, "select_directories", return_value=["C:/prestige-invalid"]), patch(
                "prestige_storage.gui.QFileDialog.getExistingDirectory", return_value="C:/output"), patch(
                "prestige_storage.gui.plan_usb_prepare", side_effect=ValueError("Brak wersji")), patch(
                "prestige_storage.gui.QMessageBox.question") as question, patch.object(
                window, "_run_usb_operation") as start:
            window.start_usb_prepare()
            question.assert_not_called()
            start.assert_not_called()
            self.assertIn("Brak wersji", window.status.text())
        window.close()

    def test_usb_prepare_shows_validated_versions_before_start(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_storage.gui import StorageWindow
        application = QApplication.instance() or QApplication([])
        window = StorageWindow(autoload=False)
        with patch.object(window, "select_directories", return_value=["C:/prestige-tool"]), patch(
                "prestige_storage.gui.QFileDialog.getExistingDirectory", return_value="C:/output"), patch(
                "prestige_storage.gui.plan_usb_prepare", return_value={
                    "destination": "C:/output/PrestigeUSB", "versions": {"prestige-tool": "1.2.3"}}), patch(
                "prestige_storage.gui.QMessageBox.question", return_value=QMessageBox.Yes) as question, patch.object(
                window, "_run_usb_operation") as start:
            window.start_usb_prepare()
            self.assertIn("prestige-tool 1.2.3", question.call_args.args[2])
            start.assert_called_once_with("prepare", "C:/output", ["C:/prestige-tool"])
        window.close()

    def test_standard_folders_merge_with_manual_without_duplicates(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_storage.gui import StorageWindow
        application = QApplication.instance() or QApplication([])
        with TemporaryDirectory() as directory:
            root = Path(directory)
            desktop = root / "Desktop"
            documents = root / "Documents"
            desktop.mkdir()
            documents.mkdir()
            window = StorageWindow(autoload=False)
            window.standard_folder_checks["Desktop"].setChecked(True)
            window.standard_folder_checks["Documents"].setChecked(True)
            with patch.object(window, "select_directories", return_value=[str(desktop)]), patch(
                    "prestige_storage.gui.known_folders", return_value={
                        "Desktop": str(desktop), "Documents": str(documents)}), patch(
                    "prestige_storage.gui.QFileDialog.getExistingDirectory", return_value=str(root)), patch(
                    "prestige_storage.gui.QMessageBox.question", return_value=QMessageBox.Yes), patch.object(
                    window, "_run_backup_operation") as start:
                window.start_backup()
                self.assertEqual(start.call_args.args[1], [str(desktop), str(documents)])
            window.close()

    def test_unavailable_standard_folder_does_not_start_backup(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_storage.gui import StorageWindow
        application = QApplication.instance() or QApplication([])
        window = StorageWindow(autoload=False)
        window.standard_folder_checks["Downloads"].setChecked(True)
        with patch.object(window, "select_directories", return_value=[]), patch(
                "prestige_storage.gui.known_folders", return_value={}), patch.object(
                window, "_run_backup_operation") as start:
            window.start_backup()
            start.assert_not_called()
            self.assertIn("Downloads", window.status.text())
        window.close()

    def test_multiple_source_selection_preserves_all_choices(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_storage.gui import StorageWindow
        application = QApplication.instance() or QApplication([])
        window = StorageWindow(autoload=False)
        with patch("prestige_storage.gui.QFileDialog.getExistingDirectory",
                   side_effect=["C:/one", "C:/two"]), patch(
                   "prestige_storage.gui.QMessageBox.question",
                   side_effect=[QMessageBox.Yes, QMessageBox.No]):
            self.assertEqual(window.select_directories("fixture"), ["C:/one", "C:/two"])
        window.close()

    def test_service_export_without_source_reaches_backup(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_storage.gui import StorageWindow
        application = QApplication.instance() or QApplication([])
        window = StorageWindow(autoload=False)
        window.system_export_checkbox.setChecked(True)
        with patch.object(window, "select_directories", return_value=[]), patch(
                "prestige_storage.gui.QFileDialog.getExistingDirectory", return_value="C:/output"), patch(
                "prestige_storage.gui.QMessageBox.question", return_value=QMessageBox.Yes), patch(
                "prestige_storage.gui.plan", return_value={"files": [], "total_bytes": 0,
                                                             "excluded_count": 0}), patch.object(
                window, "_run_backup_operation") as start:
            window.start_backup()
            start.assert_called_once()
            self.assertEqual(start.call_args.args[1], [])
        window.close()

    def test_vss_export_without_source_is_rejected(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_storage.gui import StorageWindow
        application = QApplication.instance() or QApplication([])
        window = StorageWindow(autoload=False)
        window.system_export_checkbox.setChecked(True)
        window.vss_checkbox.setChecked(True)
        with patch.object(window, "select_directories", return_value=[]), patch.object(
                window, "_run_backup_operation") as start:
            window.start_backup()
            start.assert_not_called()
            self.assertIn("VSS wymaga", window.status.text())
        window.close()

    def test_image_button_only_for_readonly_nonsystem_disk(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_storage.gui import StorageWindow
        application = QApplication.instance() or QApplication([])
        window = StorageWindow(autoload=False)
        disk = {"number": 7, "device": r"\\.\PhysicalDrive7", "model": "fixture",
                "unique_id": "fixture", "size_bytes": 4096, "bus": "USB",
                "volumes": ["E:"], "read_only": True, "system": False}
        window.show_disks([disk])
        window.table.selectRow(0)
        self.assertTrue(window.image_button.isEnabled())
        window.show_disks([dict(disk, system=True)])
        window.table.selectRow(0)
        self.assertFalse(window.image_button.isEnabled())
        window.close()

    def test_system_disk_warning_and_error_clear(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_storage.gui import StorageWindow
        application = QApplication.instance() or QApplication([])
        window = StorageWindow(autoload=False)
        window.show_disks([{
            "device": r"\\.\PhysicalDrive0", "model": "Fixture", "size_bytes": 1000,
            "bus": "USB", "volumes": ["C:"], "read_only": False, "system": True,
            "unique_id": "fixture-id",
        }])
        self.assertEqual(window.table.rowCount(), 1)
        self.assertIn("DYSK SYSTEMOWY", window.table.item(0, 5).text())
        window.table.selectRow(0)
        self.assertIn("fixture-id", window.details.text())
        window.show_error("Brak dostępu")
        self.assertEqual(window.table.rowCount(), 0)
        self.assertIn("niedostępny", window.details.text())
        self.assertIn("Brak dostępu", window.status.text())
        window.close()


if __name__ == "__main__":
    unittest.main()
