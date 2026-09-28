import tempfile
from pathlib import Path
import unittest

from prestige_core.baseline_signing import new_key, sign, verify


class BaselineSigningTests(unittest.TestCase):
    def test_sign_verify_tamper_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline.json"
            private = root / "private.pem"
            public = root / "public.pem"
            signature = root / "baseline.sig.json"
            baseline.write_text('{"files": []}', encoding="utf-8")
            new_key(private, public, "strong password")
            self.assertIn(b"ENCRYPTED PRIVATE KEY", private.read_bytes())
            sign(baseline, private, signature, "strong password")
            self.assertTrue(verify(baseline, public, signature)["ok"])
            with self.assertRaises(FileExistsError):
                sign(baseline, private, signature, "strong password")
            with self.assertRaises(ValueError):
                new_key(private, root / "other.pem", "strong password")
            baseline.write_text('{"files": [1]}', encoding="utf-8")
            self.assertFalse(verify(baseline, public, signature)["ok"])

    def test_rejects_short_password(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                new_key(root / "private.pem", root / "public.pem", "short")
