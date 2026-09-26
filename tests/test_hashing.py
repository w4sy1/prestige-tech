from pathlib import Path
import hashlib
import tempfile
import unittest

from prestige_core import FileHashService


class FileHashServiceTests(unittest.TestCase):
    def test_multiple_hashes_match_known_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dane.bin"
            content = b"prestige" * 200000
            path.write_bytes(content)
            actual = FileHashService.hashes(path, ("sha256", "sha512", "md5"))
            self.assertEqual(actual, {
                name: hashlib.new(name, content).hexdigest()
                for name in ("sha256", "sha512", "md5")
            })
            self.assertEqual(FileHashService.sha256(path), actual["sha256"])

    def test_rejects_symlink_and_unsupported_algorithm(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dane.bin"
            path.write_bytes(b"data")
            with self.assertRaises(ValueError):
                FileHashService.hashes(path, ("blake2b",))
            link = Path(folder) / "link.bin"
            try:
                link.symlink_to(path)
            except (OSError, NotImplementedError):
                return
            with self.assertRaises(ValueError):
                FileHashService.sha256(link)


if __name__ == "__main__":
    unittest.main()
