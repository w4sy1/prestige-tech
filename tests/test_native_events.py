import tempfile
import os
import stat
from pathlib import Path
from threading import Thread
import time
import unittest
from unittest.mock import Mock

from prestige_core.native_events import NativeEventStream, collect_native_events, normalize_native_capture


class NativeEventsTests(unittest.TestCase):
    def test_normalizes_rename_and_rejects_escape(self):
        result = normalize_native_capture({"overflow": False, "events": [{
            "kind": "Renamed", "path": "new.txt", "old_path": "old.txt",
            "timestamp": "2026-09-27T10:00:00Z",
        }]})
        self.assertEqual(result["events"][0]["old_path"], "old.txt")
        self.assertEqual(result["events"][0]["kind"], "Zmieniono nazwę")
        with self.assertRaises(ValueError):
            normalize_native_capture({"overflow": False, "events": [{
                "kind": "Created", "path": "..\\outside.txt", "timestamp": "now",
            }]})

    def test_overflow_is_unknown_without_events(self):
        result = normalize_native_capture({"overflow": True, "events": [{
            "kind": "Created", "path": "file.txt", "timestamp": "now",
        }]})
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["events"], [])

    def test_collection_uses_encoded_command_and_does_not_write_source(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = Mock(return_value=Mock(returncode=0, stdout='{"events":[],"overflow":false}', stderr=""))
            result = collect_native_events(directory, 0.2, runner=runner, platform="nt")
            self.assertEqual(result["events"], [])
            self.assertIn("-EncodedCommand", runner.call_args.args[0])

    @unittest.skipUnless(os.name == "nt", "Windows FileSystemWatcher")
    def test_continuous_stream_detects_transient_file_and_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            stream = NativeEventStream(directory)
            captured = []
            errors = []

            def run():
                try:
                    stream.watch(captured.append)
                except Exception as error:
                    errors.append(error)

            worker = Thread(target=run)
            worker.start()
            try:
                self.assertTrue(stream.ready.wait(6), "FileSystemWatcher nie wystartował")
                path = Path(directory) / "brief.txt"
                path.write_text("x", encoding="utf-8")
                path.unlink()
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    kinds = [event["kind"] for batch in captured for event in batch["events"]]
                    if "Nowy" in kinds and "Usunięty" in kinds:
                        break
                    time.sleep(0.05)
                self.assertIn("Nowy", kinds)
                self.assertIn("Usunięty", kinds)
            finally:
                stream.stop()
                worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])

    @unittest.skipUnless(os.name == "nt", "Windows FileSystemWatcher")
    def test_attribute_change_emits_native_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attribute.txt"
            path.write_text("x", encoding="utf-8")
            stream = NativeEventStream(directory)
            captured, errors = [], []
            def run():
                try:
                    stream.watch(captured.append)
                except Exception as error:
                    errors.append(error)
            worker = Thread(target=run)
            worker.start()
            try:
                self.assertTrue(stream.ready.wait(6))
                os.chmod(path, stat.S_IREAD)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if any(event["path"] == "attribute.txt" and event["kind"] == "Zmieniony"
                           for batch in captured for event in batch["events"]):
                        break
                    time.sleep(0.05)
                self.assertTrue(any(event["path"] == "attribute.txt" and event["kind"] == "Zmieniony"
                                    for batch in captured for event in batch["events"]))
            finally:
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                stream.stop()
                worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
