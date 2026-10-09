import tempfile
import unittest
from pathlib import Path

from prestige_core.file_snapshot import compare_files, scan_files
from prestige_core.monitor_profiles import load_profile, save_profile


class MonitorProfileTest(unittest.TestCase):
    def test_excluded_subfolder_is_not_scanned_and_profile_roundtrips(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "watched"
            root.mkdir()
            (root / "included.txt").write_text("a", encoding="utf-8")
            excluded = root / "skip"
            excluded.mkdir()
            (excluded / "private.txt").write_text("b", encoding="utf-8")
            snapshot = scan_files(root, exclude_paths=("skip",))
            self.assertTrue(snapshot["complete"])
            self.assertEqual([row["path"] for row in snapshot["files"]], ["included.txt"])
            self.assertEqual(compare_files(scan_files(root), snapshot)["status"], "UNKNOWN")
            profile_path = Path(folder) / "profile.json"
            save_profile({"schema_version": 1, "root": str(root), "extended": False,
                          "exclude_paths": ["skip"]}, profile_path)
            self.assertEqual(load_profile(profile_path)["exclude_paths"], ["skip"])
            with self.assertRaises(ValueError):
                save_profile({"schema_version": 1, "root": str(root), "extended": False,
                              "exclude_paths": ["../outside"]}, Path(folder) / "bad.json")


if __name__ == "__main__":
    unittest.main()
