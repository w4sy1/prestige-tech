import sqlite3
import tempfile
from pathlib import Path
import unittest

from prestige_core.file_snapshot import classify_file_events, scan_files
from prestige_core.watch_state import WatchStateStore


class WatchStateTests(unittest.TestCase):
    def test_state_and_events_survive_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            database = Path(directory) / "watch.sqlite"
            with WatchStateStore(root, database) as store:
                first = scan_files(root)
                store.record(first)
                (root / "new.txt").write_text("new", encoding="utf-8")
                second = scan_files(root)
                store.record(second, classify_file_events(first, second))
            with WatchStateStore(root, database) as store:
                self.assertEqual(store.load(), second)
                rows = store.connection.execute("SELECT kind, path FROM events").fetchall()
                self.assertEqual(rows, [("Nowy", "new.txt")])

    def test_rejects_database_inside_source_and_other_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            other = Path(directory) / "other"
            root.mkdir()
            other.mkdir()
            with self.assertRaises(ValueError):
                WatchStateStore(root, root / "watch.sqlite")
            database = Path(directory) / "watch.sqlite"
            with WatchStateStore(root, database):
                pass
            with self.assertRaises(ValueError):
                WatchStateStore(other, database)

    def test_rejects_unrelated_existing_database_without_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            database = Path(directory) / "unrelated.sqlite"
            connection = sqlite3.connect(database)
            try:
                connection.execute("CREATE TABLE own_data (value TEXT)")
                connection.execute("INSERT INTO own_data VALUES ('keep')")
                connection.commit()
            finally:
                connection.close()
            with self.assertRaises(ValueError):
                WatchStateStore(root, database)
            connection = sqlite3.connect(database)
            try:
                self.assertEqual(connection.execute("SELECT value FROM own_data").fetchone(), ("keep",))
                self.assertIsNone(connection.execute(
                    "SELECT name FROM sqlite_master WHERE name='metadata'").fetchone())
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
