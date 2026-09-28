import hashlib
import json
import tempfile
from pathlib import Path
from threading import Event
import unittest

from prestige_core.imaging_fixture import image_fixture_file


class ImagingFixtureTests(unittest.TestCase):
    def test_new_raw_image_is_verified_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.bin"
            destination = Path(directory) / "image.img"
            original = b"PRESTIGE" * 2000
            source.write_bytes(original)
            result = image_fixture_file(source, destination, chunk_size=4096)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertTrue(result["verified_image"])
            self.assertEqual(result["read_bytes"], len(original))
            self.assertEqual(result["sha256_image"], hashlib.sha256(original).hexdigest())
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(destination.read_bytes(), original)
            self.assertEqual(json.loads(Path(str(destination) + ".json").read_text())["status"], "COMPLETE")

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.bin"
            destination = Path(directory) / "image.img"
            source.write_bytes(b"SOURCE")
            destination.write_bytes(b"EXISTING")
            with self.assertRaises(FileExistsError):
                image_fixture_file(source, destination)
            self.assertEqual(destination.read_bytes(), b"EXISTING")
            self.assertFalse(Path(str(destination) + ".json").exists())

    def test_cancellation_is_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.bin"
            destination = Path(directory) / "image.img"
            source.write_bytes(b"SOURCE")
            event = Event()
            event.set()
            result = image_fixture_file(source, destination, cancel_event=event)
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertEqual(result["read_bytes"], 0)
            self.assertEqual(source.read_bytes(), b"SOURCE")


if __name__ == "__main__":
    unittest.main()
