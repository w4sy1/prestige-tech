"""Import baseline starego Integrity Monitor bez modyfikowania oryginału."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from prestige_core.file_snapshot import compare_files, scan_files
from prestige_core.legacy_integrity import convert_baseline


class LegacyIntegrityTests(unittest.TestCase):
    def test_complete_legacy_baseline_matches_current_scan(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "file.txt").write_text("content", encoding="utf-8")
            current = scan_files(root)
            row = current["files"][0]
            legacy = {"schema_version": 1, "root": str(root.resolve()),
                      "created_utc": "2026-09-28T00:00:00+00:00",
                      "files": {"file.txt": {key: row[key] for key in
                                             ("size", "mtime_ns", "sha256")}},
                      "options": {"extended": False},
                      "incomplete_files": [], "ok": True}
            converted = convert_baseline(legacy)
            self.assertTrue(converted["complete"])
            self.assertEqual(compare_files(converted, current)["status"], "COMPLETE")
            legacy["files"] = {"../escape": legacy["files"]["file.txt"]}
            with self.assertRaises(ValueError):
                convert_baseline(legacy)

    def test_incomplete_extended_baseline_stays_unknown(self):
        with TemporaryDirectory() as directory:
            legacy = {"schema_version": 1, "root": str(Path(directory).resolve()),
                      "files": {"a.txt": {"size": 1, "mtime_ns": 1,
                                          "sha256": "0" * 64,
                                          "extended": {"acl_status": "UNKNOWN"}}},
                      "options": {"extended": True},
                      "incomplete_files": ["a.txt"], "ok": False}
            converted = convert_baseline(legacy)
            self.assertFalse(converted["complete"])
            self.assertTrue(converted["errors"])


if __name__ == "__main__":
    unittest.main()
