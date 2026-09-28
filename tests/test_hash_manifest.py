import tempfile
from pathlib import Path
import unittest

from prestige_core.hash_manifest import compare_manifests, make_manifest, save_manifest, validate_manifest
from prestige_core.baseline_signing import new_key, sign, verify


class HashManifestTests(unittest.TestCase):
    def test_saved_manifest_can_be_signed_and_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            source.mkdir()
            (source / "one.txt").write_text("one", encoding="utf-8")
            manifest = save_manifest(make_manifest(source), base / "manifest.json")
            private, public, signature = (base / name for name in ("private.pem", "public.pem", "manifest.sig.json"))
            new_key(private, public, "strong password")
            sign(manifest, private, signature, "strong password")
            self.assertTrue(verify(manifest, public, signature)["ok"])
            manifest.write_text(manifest.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assertFalse(verify(manifest, public, signature)["ok"])

    def test_manifest_verify_change_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            path = root / "one.txt"
            path.write_text("one", encoding="utf-8")
            before = make_manifest(root, "sha512")
            output = Path(directory) / "manifest.json"
            save_manifest(before, output)
            with self.assertRaises(FileExistsError):
                save_manifest(before, output)
            path.write_text("two", encoding="utf-8")
            after = make_manifest(root, "sha512")
            self.assertEqual(compare_manifests(before, after)["changed"], ["one.txt"])
            self.assertEqual(compare_manifests(before, before)["ok"], True)

    def test_rejects_path_escape_and_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            data = make_manifest(directory)
            bad = dict(data, files={"../escape": {"hash": "0" * 64}})
            with self.assertRaises(ValueError):
                validate_manifest(bad)
            bad = dict(data, complete=False)
            with self.assertRaises(ValueError):
                save_manifest(bad, Path(directory).parent / "manifest.json")
