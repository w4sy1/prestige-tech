import os
import tempfile
import unittest
from pathlib import Path

from prestige_core.system_snapshot import (QUERIES, compare, load_snapshot,
                                           save_snapshot, validate_snapshot)


def snapshot(**overrides):
    sections = {name: {"status": "OK", "data": []} for name in QUERIES}
    sections.update(overrides)
    return {"schema_version": 1, "created_utc": "2026-01-01T00:00:00+00:00",
            "sections": sections}


class SystemSnapshotTests(unittest.TestCase):
    def test_save_compare_identity_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            before = snapshot(programs={"status": "OK", "data": [
                {"RegistryKey": "HKLM/a", "DisplayVersion": "1"}]})
            after = snapshot(programs={"status": "OK", "data": [
                {"RegistryKey": "HKLM/a", "DisplayVersion": "2"}]})
            path = Path(directory) / "snapshot.json"
            save_snapshot(before, path)
            with self.assertRaises(FileExistsError):
                save_snapshot(after, path)
            self.assertEqual(load_snapshot(path), before)
            changes = compare(before, after)["sections"]["programs"]["identified_changes"]
            self.assertEqual(changes["modified"][0]["changed_fields"], ["DisplayVersion"])

    def test_unknown_or_missing_section_not_clean(self):
        before = snapshot()
        after = snapshot(security={"status": "UNKNOWN", "data": []})
        self.assertEqual(compare(before, after)["sections"]["security"]["status"], "UNKNOWN")
        del after["sections"]["security"]
        with self.assertRaises(ValueError):
            validate_snapshot(after)

    def test_snapshot_file_size_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            save_snapshot(snapshot(), path)
            with self.assertRaises(ValueError):
                load_snapshot(path, max_bytes=1)


class SystemSnapshotGuiTests(unittest.TestCase):
    def test_capture_and_compare_controls_exist(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_system.gui import SystemCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SystemCenterWindow()
        self.assertTrue(window.capture_button.isEnabled())
        self.assertTrue(window.compare_button.isEnabled())
        window.close()
