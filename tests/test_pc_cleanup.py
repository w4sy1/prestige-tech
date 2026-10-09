import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from prestige_core.pc_cleanup import clean, restore, scan, scan_usage


def aged(path):
    path.write_text("fixture", encoding="utf-8")
    old = time.time() - 10 * 86400
    os.utime(path, (old, old))


class PCCleanupTests(unittest.TestCase):
    def test_usage_scan_is_read_only_and_skips_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "small.txt").write_bytes(b"a")
            (root / "large.txt").write_bytes(b"a" * 20)
            result = scan_usage(root)
            self.assertEqual(result["total_bytes"], 21)
            self.assertEqual(result["largest_files"][0]["path"], "large.txt")
            self.assertFalse(result["clean_allowed"])
            self.assertTrue((root / "large.txt").exists())

    def test_fixture_quarantine_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "temp"
            source.mkdir()
            file = source / "old.log"
            aged(file)
            quarantine = Path(directory) / "quarantine"
            with patch("prestige_core.pc_cleanup.temp_roots", return_value=[source.resolve()]):
                plan = scan(source)
                self.assertTrue(plan["clean_allowed"])
                self.assertEqual(clean(plan, quarantine)["moved"], 1)
                self.assertFalse(file.exists())
                self.assertEqual(restore(quarantine)["restored"], 1)
                self.assertEqual(file.read_text(encoding="utf-8"), "fixture")

    def test_changed_file_rejected_before_move(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "temp"
            source.mkdir()
            file = source / "old.log"
            aged(file)
            with patch("prestige_core.pc_cleanup.temp_roots", return_value=[source.resolve()]):
                plan = scan(source)
                file.write_text("changed", encoding="utf-8")
                with self.assertRaises(ValueError):
                    clean(plan, Path(directory) / "quarantine")
                self.assertTrue(file.exists())

    def test_personal_folder_cannot_be_cleaned(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "personal"
            source.mkdir()
            aged(source / "old.log")
            with patch("prestige_core.pc_cleanup.temp_roots", return_value=[]):
                plan = scan(source)
                self.assertFalse(plan["clean_allowed"])
                with self.assertRaises(ValueError):
                    clean(plan, Path(directory) / "quarantine")

    def test_restore_refuses_target_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "temp"
            source.mkdir()
            file = source / "old.log"
            aged(file)
            quarantine = Path(directory) / "quarantine"
            with patch("prestige_core.pc_cleanup.temp_roots", return_value=[source.resolve()]):
                clean(scan(source), quarantine)
                file.write_text("new user file", encoding="utf-8")
                with self.assertRaises(ValueError):
                    restore(quarantine)
                self.assertEqual(file.read_text(encoding="utf-8"), "new user file")


class PCCleanupGuiTests(unittest.TestCase):
    def test_cleanup_requires_plan_before_apply(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_system.gui import SystemCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SystemCenterWindow()
        self.assertFalse(window.cleanup_apply_button.isEnabled())
        self.assertTrue(window.cleanup_scan_button.isEnabled())
        window.close()
