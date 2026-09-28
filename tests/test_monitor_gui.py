import os
import tempfile
from pathlib import Path
import time
import unittest
from unittest.mock import patch
import json


class MonitorGuiTests(unittest.TestCase):
    def test_import_old_integrity_baseline_creates_new_file(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_monitor.gui import MonitorWindow
        application = QApplication.instance() or QApplication([])
        window = MonitorWindow()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            old_file = Path(directory) / "old.json"
            new_file = Path(directory) / "new.json"
            old = {"schema_version": 1, "root": str(root.resolve()),
                   "files": {"file.txt": {"sha256": "0" * 64,
                                          "size": 1, "mtime_ns": 1}},
                   "options": {"extended": False},
                   "incomplete_files": [], "ok": True}
            old_file.write_text(json.dumps(old), encoding="utf-8")
            with patch("prestige_monitor.gui.QFileDialog.getOpenFileName",
                       return_value=(str(old_file), "")), patch(
                       "prestige_monitor.gui.QFileDialog.getSaveFileName",
                       return_value=(str(new_file), "")):
                window.load_baseline()
            self.assertEqual(window.baseline_path, str(new_file.resolve()))
            self.assertIsInstance(json.loads(new_file.read_text())["files"], list)
            self.assertEqual(json.loads(old_file.read_text()), old)
        window.close()

    def test_scan_result_and_error_clear_stale_rows(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_monitor.gui import MonitorWindow
        application = QApplication.instance() or QApplication([])
        window = MonitorWindow()
        with tempfile.TemporaryDirectory() as directory:
            window.set_folder(directory)
            self.assertTrue(window.scan_button.isEnabled())
            window.show_events({
                "status": "COMPLETE", "added": ["alpha.txt", "beta.log"],
                "removed": [], "changed": [],
            })
            self.assertEqual(window.events_table.rowCount(), 2)
            window.event_filter.setText("alpha")
            self.assertEqual(window.events_table.rowCount(), 1)
            self.assertTrue(window.history_dirty)
            with self.assertRaises(ValueError):
                window.set_folder(directory)
            window.show_snapshot({
                "schema_version": 1, "root": str(Path(directory).resolve()),
                "files": [{"path": "file.txt", "sha256": "abc"}],
                "errors": [], "complete": True,
            })
            self.assertEqual(window.table.rowCount(), 1)
            self.assertTrue(window.save_button.isEnabled())
            window.baseline = {
                "schema_version": 1, "root": str(Path(directory).resolve()),
                "files": [{"path": "gone.txt", "sha256": "old"}],
                "errors": [], "complete": True,
            }
            window.show_snapshot({
                "schema_version": 1, "root": str(Path(directory).resolve()),
                "files": [{"path": "file.txt", "sha256": "abc"}],
                "errors": [], "complete": True,
            })
            self.assertEqual(window.table.rowCount(), 2)
            self.assertEqual(window.table.item(1, 2).text(), "Usunięty")
            window.show_error("Odmowa dostępu")
            self.assertEqual(window.table.rowCount(), 0)
            self.assertFalse(window.save_button.isEnabled())
        window.close()

    def test_live_watch_detects_new_file_and_stops(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_core.file_snapshot import scan_files
        from prestige_core.watch_state import WatchStateStore
        from prestige_monitor.gui import WatchWorker
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            worker = WatchWorker(directory)
            changes = []
            worker.changed.connect(changes.append)
            worker.start()
            time.sleep(0.3)
            (Path(directory) / "new.txt").write_text("new", encoding="utf-8")
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not changes:
                application.processEvents()
                time.sleep(0.05)
            worker.stop_event.set()
            self.assertTrue(worker.wait(3000))
            application.processEvents()
            self.assertTrue(changes)
            self.assertEqual(changes[0]["added"], ["new.txt"])

    def test_sqlite_watch_resumes_changes_from_previous_session(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_core.file_snapshot import scan_files
        from prestige_core.watch_state import WatchStateStore
        from prestige_monitor.gui import MonitorWindow, WatchWorker
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            database = Path(directory) / "state.sqlite"
            with WatchStateStore(root, database) as store:
                store.record(scan_files(root))
            (root / "offline.txt").write_text("new", encoding="utf-8")
            window = MonitorWindow()
            window.set_folder(root)
            window.set_state_database(database)
            self.assertEqual(window.state_path, str(database))
            worker = WatchWorker(root, state_path=database)
            changes = []
            worker.changed.connect(changes.append)
            worker.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not changes:
                application.processEvents()
                time.sleep(0.02)
            worker.stop_event.set()
            self.assertTrue(worker.wait(3000))
            application.processEvents()
            self.assertEqual(changes[0]["added"], ["offline.txt"])
            with WatchStateStore(root, database) as store:
                self.assertEqual(store.load_events()[0]["path"], "offline.txt")
            window.close()

    def test_sqlite_resume_rehashes_file_even_with_same_size_and_mtime(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_core.file_snapshot import scan_files
        from prestige_core.watch_state import WatchStateStore
        from prestige_monitor.gui import WatchWorker
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            path = root / "file.txt"
            path.write_bytes(b"first")
            stamp = path.stat().st_mtime_ns
            database = Path(directory) / "state.sqlite"
            with WatchStateStore(root, database) as store:
                store.record(scan_files(root))
            path.write_bytes(b"other")
            os.utime(path, ns=(stamp, stamp))
            worker = WatchWorker(root, state_path=database)
            changes = []
            worker.changed.connect(changes.append)
            worker.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not changes:
                application.processEvents()
                time.sleep(0.02)
            worker.stop_event.set()
            self.assertTrue(worker.wait(3000))
            application.processEvents()
            self.assertEqual(changes[0]["changed"], ["file.txt"])

    @unittest.skipUnless(os.name == "nt", "ACL/ADS wymaga Windows")
    def test_extended_watch_detects_ads_change(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_core.file_snapshot import scan_files
        from prestige_core.watch_state import WatchStateStore
        from prestige_monitor.gui import WatchWorker
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "file.txt"
            file.write_text("main", encoding="utf-8")
            ads = Path(str(file) + ":prestige-test")
            ads.write_text("one", encoding="utf-8")
            database = Path(directory).parent / (Path(directory).name + "-watch.sqlite")
            with WatchStateStore(directory, database) as store:
                store.record(scan_files(directory, extended=True))
            worker = WatchWorker(directory, state_path=database, extended=True)
            changes = []
            worker.changed.connect(changes.append)
            worker.start()
            time.sleep(0.8)
            ads.write_text("two", encoding="utf-8")
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline and not changes:
                application.processEvents()
                time.sleep(0.05)
            worker.stop_event.set()
            self.assertTrue(worker.wait(4000))
            application.processEvents()
            self.assertTrue(changes)
            self.assertEqual(changes[0]["changed"], ["file.txt"])
            database.unlink(missing_ok=True)

    def test_watch_rejects_sqlite_mode_mismatch(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_core.file_snapshot import scan_files
        from prestige_core.watch_state import WatchStateStore
        from prestige_monitor.gui import WatchWorker
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            database = Path(directory) / "state.sqlite"
            with WatchStateStore(root, database) as store:
                store.record(scan_files(root))
            worker = WatchWorker(root, state_path=database, extended=True)
            failures = []
            worker.failed.connect(failures.append)
            worker.start()
            self.assertTrue(worker.wait(3000))
            application.processEvents()
            self.assertIn("inny tryb ACL/ADS", failures[0])

    @unittest.skipUnless(os.name == "nt", "Windows FileSystemWatcher")
    def test_gui_continuous_native_watch_receives_and_stops(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_monitor.gui import MonitorWindow
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            window = MonitorWindow()
            window.set_folder(directory)
            window.toggle_native_stream()
            self.assertTrue(window.native_stream_worker.stream.ready.wait(6))
            path = Path(directory) / "brief.txt"
            path.write_text("x", encoding="utf-8")
            path.unlink()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                application.processEvents()
                kinds = [row["kind"] for row in window.history["events"]]
                if "Nowy" in kinds and "Usunięty" in kinds:
                    break
                time.sleep(0.05)
            self.assertIn("Nowy", kinds)
            self.assertIn("Usunięty", kinds)
            window.toggle_native_stream()
            self.assertTrue(window.native_stream_worker.wait(3000))
            application.processEvents()
            self.assertEqual(window.native_stream_button.text(), "Natywnie: start")
            window.close()


if __name__ == "__main__":
    unittest.main()
