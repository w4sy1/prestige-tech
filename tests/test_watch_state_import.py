import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from prestige_core.watch_state import WatchStateStore
from prestige_core.watch_state_import import import_legacy_watch_database


class WatchStateImportTests(unittest.TestCase):
    def _legacy(self, source, root, *, path="old.txt"):
        connection = sqlite3.connect(source)
        try:
            connection.executescript(
                "CREATE TABLE metadata(root TEXT);"
                "CREATE TABLE state(path TEXT PRIMARY KEY, data TEXT);"
                "CREATE TABLE events(id INTEGER PRIMARY KEY, timestamp TEXT, type TEXT, path TEXT, old_path TEXT, sha256 TEXT);"
            )
            connection.execute("INSERT INTO metadata VALUES (?)", (str(root),))
            connection.execute("INSERT INTO state VALUES (?, ?)", (path, json.dumps({
                "sha256": "a" * 64, "size": 3, "mtime_ns": 123, "inode": 5,
            })))
            connection.execute("INSERT INTO events(timestamp,type,path,old_path,sha256) VALUES (?,?,?,?,?)",
                               ("2026-09-27T10:00:00+00:00", "rename", "new.txt", "old.txt", "a" * 64))
            connection.commit()
        finally:
            connection.close()

    def test_imports_to_new_database_without_touching_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            old = Path(directory) / "old.sqlite"
            new = Path(directory) / "new.sqlite"
            self._legacy(old, root)
            original_bytes = old.read_bytes()
            result = import_legacy_watch_database(old, root, new)
            self.assertEqual(result["files"], 1)
            self.assertEqual(result["events"], 1)
            self.assertEqual(old.read_bytes(), original_bytes)
            with WatchStateStore(root, new) as store:
                self.assertTrue(store.load()["capture_time_unknown"])
                self.assertEqual(store.load_events()[0]["old_path"], "old.txt")
            with self.assertRaises(FileExistsError):
                import_legacy_watch_database(old, root, new)

    def test_rejects_escape_without_creating_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            old = Path(directory) / "old.sqlite"
            new = Path(directory) / "new.sqlite"
            self._legacy(old, root, path="..\\outside.txt")
            with self.assertRaises(ValueError):
                import_legacy_watch_database(old, root, new)
            self.assertFalse(new.exists())

    def test_imports_native_event_only_database_without_fabricating_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            old = Path(directory) / "native.sqlite"
            new = Path(directory) / "new.sqlite"
            connection = sqlite3.connect(old)
            try:
                connection.executescript(
                    "CREATE TABLE metadata(root TEXT);"
                    "CREATE TABLE events(id INTEGER PRIMARY KEY, timestamp TEXT, type TEXT, path TEXT, old_path TEXT, sha256 TEXT);"
                )
                connection.execute("INSERT INTO metadata VALUES (?)", (str(root),))
                connection.execute("INSERT INTO events(timestamp,type,path,old_path,sha256) VALUES (?,?,?,?,?)",
                                   ("2026-09-27T10:00:00+00:00", "create", "new.txt", None, "a" * 64))
                connection.commit()
            finally:
                connection.close()
            original_bytes = old.read_bytes()
            result = import_legacy_watch_database(old, root, new)
            self.assertFalse(result["baseline_imported"])
            self.assertEqual(result["events"], 1)
            self.assertEqual(old.read_bytes(), original_bytes)
            with WatchStateStore(root, new) as store:
                self.assertIsNone(store.load())
                self.assertEqual(store.load_events()[0]["path"], "new.txt")


if __name__ == "__main__":
    unittest.main()
