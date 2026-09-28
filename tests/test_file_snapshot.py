import os
import tempfile
from pathlib import Path
from threading import Event
import unittest
from unittest.mock import patch

from prestige_core.file_snapshot import classify_file_events, compare_files, scan_files


class FileSnapshotTests(unittest.TestCase):
    def test_detects_added_and_modified_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.txt").write_text("old", encoding="utf-8")
            before = scan_files(root)
            (root / "one.txt").write_text("new", encoding="utf-8")
            (root / "two.txt").write_text("new", encoding="utf-8")
            after = scan_files(root)
            self.assertTrue(before["complete"])
            self.assertEqual(compare_files(before, after), {
                "status": "COMPLETE", "added": ["two.txt"],
                "removed": [], "changed": ["one.txt"],
            })

    def test_limit_marks_comparison_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.txt").write_text("1", encoding="utf-8")
            (root / "two.txt").write_text("2", encoding="utf-8")
            incomplete = scan_files(root, max_files=1)
            self.assertFalse(incomplete["complete"])
            self.assertEqual(compare_files(incomplete, scan_files(root))["status"], "UNKNOWN")

    def test_access_denied_does_not_appear_as_file_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.txt").write_text("data", encoding="utf-8")
            before = scan_files(root)
            with patch("prestige_core.file_snapshot.os.scandir", side_effect=PermissionError("denied")):
                after = scan_files(root)
            self.assertFalse(after["complete"])
            self.assertEqual(compare_files(before, after)["status"], "UNKNOWN")
            self.assertTrue(any("denied" in row["error"] for row in after["errors"]))

    def test_cancel_marks_snapshot_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            event = Event()
            event.set()
            snapshot = scan_files(directory, cancel_event=event)
            self.assertFalse(snapshot["complete"])
            self.assertIn("przerwany", snapshot["errors"][0]["error"])

    def test_watch_reuses_unchanged_hash_and_rehashes_changed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "watch.txt"
            path.write_text("one", encoding="utf-8")
            first = scan_files(directory)
            with patch("prestige_core.file_snapshot.FileHashService.sha256") as hash_file:
                second = scan_files(directory, previous=first)
                hash_file.assert_not_called()
            self.assertEqual(second["files"][0]["sha256"], first["files"][0]["sha256"])
            path.write_text("longer content", encoding="utf-8")
            with patch("prestige_core.file_snapshot.FileHashService.sha256", return_value="changed") as hash_file:
                third = scan_files(directory, previous=second)
                hash_file.assert_called_once()
            self.assertEqual(third["files"][0]["sha256"], "changed")

    def test_forced_rehash_detects_content_change_with_unchanged_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "watch.txt"
            path.write_bytes(b"first")
            first = scan_files(directory)
            original_mtime = path.stat().st_mtime_ns
            path.write_bytes(b"other")
            os.utime(path, ns=(original_mtime, original_mtime))
            cached = scan_files(directory, previous=first)
            self.assertEqual(compare_files(first, cached)["changed"], [])
            refreshed = scan_files(directory, previous=cached, force_rehash=True)
            self.assertEqual(compare_files(first, refreshed)["changed"], ["watch.txt"])

    def test_classifies_rename_when_inode_and_hash_match(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path(directory) / "old.txt"
            old.write_text("content", encoding="utf-8")
            before = scan_files(directory)
            old.rename(Path(directory) / "new.txt")
            after = scan_files(directory)
            result = classify_file_events(before, after)
            self.assertEqual(result["renamed"], [{"old_path": "old.txt", "path": "new.txt"}])
            self.assertEqual(result["added"], [])
            self.assertEqual(result["removed"], [])

    def test_does_not_guess_rename_from_matching_content_alone(self):
        before = {"schema_version": 1, "root": "root", "complete": True,
                  "files": [{"path": "old", "sha256": "same", "inode": 1}]}
        after = {"schema_version": 1, "root": "root", "complete": True,
                 "files": [{"path": "new", "sha256": "same", "inode": 2}]}
        result = classify_file_events(before, after)
        self.assertEqual(result["renamed"], [])
        self.assertEqual(result["added"], ["new"])
        self.assertEqual(result["removed"], ["old"])

    def test_classifies_metadata_only_modification_for_watch(self):
        before = {"schema_version": 1, "root": "root", "complete": True,
                  "files": [{"path": "file", "sha256": "same", "mtime_ns": 1}]}
        after = {"schema_version": 1, "root": "root", "complete": True,
                 "files": [{"path": "file", "sha256": "same", "mtime_ns": 2}]}
        self.assertEqual(compare_files(before, after)["changed"], [])
        self.assertEqual(classify_file_events(before, after)["changed"], ["file"])

    def test_extended_metadata_change_and_mixed_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a.txt"
            path.write_text("same", encoding="utf-8")
            first_metadata = {"a.txt": {"sddl": "D:ONE", "acl_status": "OK",
                                        "ads_status": "OK", "streams": []}}
            second_metadata = {"a.txt": {"sddl": "D:TWO", "acl_status": "OK",
                                         "ads_status": "OK", "streams": []}}
            with patch("prestige_core.file_snapshot.collect_extended", return_value=first_metadata):
                before = scan_files(directory, extended=True)
            with patch("prestige_core.file_snapshot.collect_extended", return_value=second_metadata):
                after = scan_files(directory, extended=True)
            self.assertTrue(before["complete"])
            self.assertEqual(compare_files(before, after)["changed"], ["a.txt"])
            self.assertEqual(compare_files(before, scan_files(directory))["status"], "UNKNOWN")
            tampered = dict(before)
            tampered["files"] = [dict(before["files"][0], extended={"acl_status": "OK", "ads_status": "OK", "streams": []})]
            self.assertEqual(compare_files(tampered, after)["status"], "UNKNOWN")

    def test_incomplete_extended_metadata_never_looks_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "a.txt").write_text("x", encoding="utf-8")
            with patch("prestige_core.file_snapshot.collect_extended", return_value={
                "a.txt": {"acl_status": "UNKNOWN", "ads_status": "OK", "streams": []}
            }):
                snapshot = scan_files(directory, extended=True)
            self.assertFalse(snapshot["complete"])
            self.assertEqual(compare_files(snapshot, snapshot)["status"], "UNKNOWN")

    @unittest.skipUnless(os.name == "nt", "ADS wymaga Windows")
    def test_real_ads_change_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("main", encoding="utf-8")
            ads = root / "a.txt:prestige-test"
            ads.write_text("one", encoding="utf-8")
            before = scan_files(root, extended=True)
            ads.write_text("two", encoding="utf-8")
            after = scan_files(root, extended=True)
            self.assertTrue(before["complete"], before["errors"])
            self.assertTrue(after["complete"], after["errors"])
            self.assertEqual(compare_files(before, after)["changed"], ["a.txt"])


if __name__ == "__main__":
    unittest.main()
