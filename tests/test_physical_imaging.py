import io
import tempfile
from pathlib import Path
from threading import Event
import unittest

from prestige_core.physical_imaging import image_readonly_disk


class PhysicalImagingTests(unittest.TestCase):
    def disk(self, size, *, read_only=True, system=False):
        return {"number": 7, "device": r"\\.\PhysicalDrive7", "unique_id": "fixture-7",
                "size_bytes": size, "read_only": read_only, "system": system}

    def test_fixture_copy_verify_and_no_source_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            data = b"PRESTIGE" * 1024
            calls = []
            def opener(path, mode, **kwargs):
                calls.append((path, mode))
                return io.BytesIO(data)
            destination = Path(directory) / "disk.img"
            result = image_readonly_disk(7, destination, disks_reader=lambda: [self.disk(len(data))],
                                         target_resolver=lambda path: 8, source_opener=opener,
                                         chunk_size=4096, platform="nt")
            self.assertEqual(result["status"], "COMPLETE")
            self.assertTrue(result["verified_image"])
            self.assertEqual(destination.read_bytes(), data)
            self.assertEqual(calls, [(r"\\.\PhysicalDrive7", "rb")])
            with self.assertRaises(FileExistsError):
                image_readonly_disk(7, destination, disks_reader=lambda: [self.disk(len(data))],
                                    target_resolver=lambda path: 8, source_opener=opener, platform="nt")

    def test_rejects_writable_system_or_same_target(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "disk.img"
            for disk, target in ((self.disk(4, read_only=False), 8),
                                 (self.disk(4, system=True), 8), (self.disk(4), 7)):
                with self.assertRaises(ValueError):
                    image_readonly_disk(7, destination, disks_reader=lambda: [disk],
                                        target_resolver=lambda path: target, platform="nt")
            self.assertFalse(destination.exists())

    def test_cancel_marks_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            event = Event()
            event.set()
            destination = Path(directory) / "disk.img"
            result = image_readonly_disk(7, destination, cancel_event=event,
                                         disks_reader=lambda: [self.disk(4096)],
                                         target_resolver=lambda path: 8,
                                         source_opener=lambda *a, **kw: io.BytesIO(b"x" * 4096),
                                         platform="nt")
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertEqual(result["read_bytes"], 0)
