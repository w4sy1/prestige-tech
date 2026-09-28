import hashlib
import os
import tempfile
import unittest
from pathlib import Path

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


class SecurityGuiTests(unittest.TestCase):
    def test_window_has_real_inspection_action(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_security.gui import SecurityCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SecurityCenterWindow()
        self.assertTrue(window.choose_button.isEnabled())
        self.assertFalse(window.strings_checkbox.isChecked())
        window.close()
