import tempfile
from pathlib import Path
import unittest

from prestige_core.event_history import EventJournal, append_comparison, load_history, load_journal, new_history, save_history


class EventHistoryTests(unittest.TestCase):
    def test_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            history = new_history(directory)
            append_comparison(history, {
                "status": "COMPLETE", "added": ["new.txt"],
                "removed": ["gone.txt"], "changed": ["edited.txt"],
            }, observed_at="2026-09-27T12:00:00+00:00")
            path = Path(directory).parent / (Path(directory).name + "-history.json")
            try:
                save_history(history, path)
                self.assertEqual(load_history(path), history)
                with self.assertRaises(FileExistsError):
                    save_history(history, path)
            finally:
                path.unlink(missing_ok=True)

    def test_incomplete_comparison_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            history = new_history(directory)
            with self.assertRaises(ValueError):
                append_comparison(history, {"status": "UNKNOWN"})
            self.assertEqual(history["events"], [])

    def test_rename_history_preserves_old_path(self):
        with tempfile.TemporaryDirectory() as directory:
            history = new_history(directory)
            append_comparison(history, {
                "status": "COMPLETE", "added": [], "removed": [], "changed": [],
                "renamed": [{"old_path": "old.txt", "path": "new.txt"}],
            })
            self.assertEqual(history["events"][0]["old_path"], "old.txt")
            self.assertEqual(history["events"][0]["kind"], "Zmieniono nazwę")
            path = Path(directory).parent / (Path(directory).name + "-rename.json")
            try:
                save_history(history, path)
                self.assertEqual(load_history(path), history)
            finally:
                path.unlink(missing_ok=True)

    def test_journal_is_outside_source_and_appends_durably(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "watched"
            root.mkdir()
            history = new_history(root)
            with self.assertRaises(ValueError):
                EventJournal(history, root / "events.jsonl")
            self.assertFalse((root / "events.jsonl").exists())
            path = Path(directory) / "events.jsonl"
            journal = EventJournal(history, path)
            append_comparison(history, {
                "status": "COMPLETE", "added": ["file.txt"],
                "removed": [], "changed": [],
            }, observed_at="2026-09-27T12:00:00+00:00")
            journal.append(history["events"])
            journal.close()
            self.assertEqual(load_journal(path), history)
            with self.assertRaises(FileExistsError):
                EventJournal(history, path)


if __name__ == "__main__":
    unittest.main()
