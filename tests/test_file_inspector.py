import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prestige_core.file_inspector import inspect_file


class FileInspectorTests(unittest.TestCase):
    def test_pdf_hash_entropy_and_optional_strings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.pdf"
            content = b"%PDF-1.7\nprivate-value-123456\n"
            path.write_bytes(content)
            result = inspect_file(path, platform="posix")
            self.assertEqual(result["hashes"]["sha256"], hashlib.sha256(content).hexdigest())
            self.assertEqual(result["mime_by_magic"], "application/pdf")
            self.assertEqual(result["signature"]["status"], "UNAVAILABLE")
            self.assertEqual(result["strings"], [])
            self.assertGreater(result["entropy_bits_per_byte"], 0)
            with_strings = inspect_file(path, include_strings=True, platform="posix")
            self.assertTrue(any("private-value" in value for value in with_strings["strings"]))

    def test_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.bin"
            target.write_bytes(b"abc")
            link = Path(directory) / "link.bin"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Dowiązania niedostępne w tym środowisku")
            with self.assertRaises(ValueError):
                inspect_file(link, platform="posix")

    def test_hashes_and_entropy_use_one_file_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.bin"
            content = b"abc" * 1000
            path.write_bytes(content)
            original_open = Path.open
            reads = []

            def tracked_open(candidate, *args, **kwargs):
                if candidate == path:
                    reads.append(args[0] if args else kwargs.get("mode", "r"))
                return original_open(candidate, *args, **kwargs)

            with patch.object(Path, "open", tracked_open):
                result = inspect_file(path, platform="posix")
            self.assertEqual(reads, ["rb"])
            self.assertEqual(result["hashes"]["sha256"], hashlib.sha256(content).hexdigest())


class SecurityGuiTests(unittest.TestCase):
    def test_window_has_real_inspection_action(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_security.gui import SecurityCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SecurityCenterWindow()
        self.assertTrue(window.choose_button.isEnabled())
        self.assertFalse(window.strings_checkbox.isChecked())
        self.assertFalse(window.export_file_button.isEnabled())
        window.close()

    def test_gui_exports_only_completed_file_result(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_security.gui import SecurityCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SecurityCenterWindow()
        with tempfile.TemporaryDirectory() as directory:
            with patch("prestige_security.gui.QFileDialog.getExistingDirectory", return_value=directory):
                window.export_file_report()
                self.assertEqual(list(Path(directory).iterdir()), [])
                window.show_result({"action": "file", "data": {"name": "sample.bin", "strings": []}})
                self.assertTrue(window.export_file_button.isEnabled())
                window.export_file_report()
            files = list(Path(directory).iterdir())
            self.assertEqual({path.suffix for path in files}, {".json", ".txt", ".html"})
            window.show_error("odmowa dostępu")
            self.assertFalse(window.export_file_button.isEnabled())
            self.assertIsNone(window.file_result)
        window.close()
