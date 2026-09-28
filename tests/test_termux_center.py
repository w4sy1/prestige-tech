import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

from prestige_core.termux_configuration import configure, restore
from prestige_core.termux_toolkit import CATEGORIES, OPERATIONS, command
from termux_center import main


class TermuxCenterTests(unittest.TestCase):
    def test_setup_plan_and_toolkit_dependencies_share_entry(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["setup", "--profile", "network"]), 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["dry_run"])
        self.assertIn("nmap", data["plan"]["packages"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["toolkit", "DIAGNOSTICS", "--operation", "dependencies"]), 0)
        self.assertIn("pkg", json.loads(output.getvalue()))

    def test_setup_backup_restore_and_changed_file_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = configure(home, git_name="Test User", git_email="test@example.invalid", ssh_client=True)
            self.assertTrue(result["changed"])
            self.assertTrue((home / ".bashrc").exists())
            self.assertTrue((home / ".ssh" / "config").exists())
            (home / ".bashrc").write_text("zmieniony po instalacji", encoding="utf-8")
            with self.assertRaises(ValueError):
                restore(home, result["backup"])
            self.assertTrue((home / ".gitconfig").exists())

    def test_setup_restore_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".bashrc").write_text("oryginał\n", encoding="utf-8")
            result = configure(home)
            restored = restore(home, result["backup"])
            self.assertTrue(restored["restored"])
            self.assertEqual((home / ".bashrc").read_text(encoding="utf-8"), "oryginał\n")

    def test_all_toolkit_categories_and_ping_validation(self):
        self.assertEqual(len(CATEGORIES), 8)
        self.assertTrue(all(OPERATIONS[name] for name in CATEGORIES))
        self.assertEqual(command("NETWORK", ".", "ping", "2001:db8::1")[-1], "2001:db8::1")
        with self.assertRaises(ValueError):
            command("NETWORK", ".", "ping", "example.com;rm")

    @unittest.skipUnless(shutil.which("tar"), "tar unavailable")
    def test_toolkit_backup_and_hash_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            (source / "notes.txt").write_text("dane testowe", encoding="utf-8")
            (source / ".env").write_text("TEST_SECRET=fixture", encoding="utf-8")
            archive = Path(directory) / "backup.tar.gz"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["toolkit", "BACKUP", "--operation", "create",
                                       "--root", str(source), "--archive", str(archive)]), 0)
            self.assertIn("plan", json.loads(output.getvalue()))
            self.assertFalse(archive.exists())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["toolkit", "BACKUP", "--operation", "create",
                                       "--root", str(source), "--archive", str(archive), "--apply"]), 0)
            self.assertTrue(archive.is_file())
            with tarfile.open(archive, "r:gz") as stream:
                names = stream.getnames()
            self.assertTrue(any(name.endswith("notes.txt") for name in names))
            self.assertFalse(any(name.endswith(".env") for name in names))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["toolkit", "BACKUP", "--operation", "verify",
                                       "--archive", str(archive)]), 0)
            self.assertTrue(json.loads(output.getvalue())["ok"])


class TermuxGuiTests(unittest.TestCase):
    def test_setup_and_toolkit_controls(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_termux.gui import TermuxCenterWindow
        app = QApplication.instance() or QApplication([])
        window = TermuxCenterWindow()
        self.assertEqual(window.area.count(), 2)
        self.assertTrue(window.profile.isEnabled())
        window.area.setCurrentText("Toolkit")
        self.assertTrue(window.category.isEnabled())
        self.assertEqual(window.category.count(), 8)
        window.close()
