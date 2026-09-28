"""Kopia w Center nie zależy od starego repozytorium i zachowuje manifest."""

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from prestige_core.backup import backup, plan, restore, verify


class BackupMigrationTests(unittest.TestCase):
    def test_bookmarks_only_backup_has_verifiable_manifest(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            bookmarks = root / "Bookmarks"
            bookmarks.write_text(json.dumps({"roots": {"bookmark_bar": {
                "type": "folder", "name": "bar", "children": [{
                    "type": "url", "name": "site", "url": "https://example.org/path?private=1"}]}}}),
                encoding="utf-8")
            destination = root / "backup"
            self.assertTrue(backup([], destination, bookmarks=[bookmarks])["ok"])
            self.assertTrue(verify(destination)["ok"])
            exported = json.loads((destination / "_service/bookmarks-1.json").read_text(encoding="utf-8"))
            self.assertEqual(exported["roots"]["bookmark_bar"]["children"][0]["url"],
                             "https://example.org/path")

    def test_multiple_sources_keep_distinct_paths(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            sources = []
            for name in ("documents", "photos"):
                source = root / name
                source.mkdir()
                (source / "same.txt").write_text(name, encoding="utf-8")
                sources.append(source)
            destination = root / "backup"
            self.assertTrue(backup(sources, destination)["ok"])
            self.assertTrue(verify(destination)["ok"])
            self.assertEqual((destination / "1-documents/same.txt").read_text(), "documents")
            self.assertEqual((destination / "2-photos/same.txt").read_text(), "photos")

    def test_backup_verify_restore_and_refuse_tampering(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source"
            source.mkdir()
            (source / "photo.txt").write_text("content", encoding="utf-8")
            (source / ".env").write_text("excluded", encoding="utf-8")
            self.assertEqual(plan([source])["excluded_count"], 1)
            copied = root / "copied"
            self.assertTrue(backup([source], copied)["ok"])
            self.assertTrue(verify(copied)["ok"])
            destination = root / "restored"
            self.assertFalse(restore(copied, destination)["executed"])
            self.assertTrue(restore(copied, destination, apply=True)["ok"])
            self.assertEqual((destination / "1-source" / "photo.txt").read_text(), "content")
            self.assertFalse((destination / "1-source" / ".env").exists())
            (copied / "1-source" / "photo.txt").write_text("changed")
            self.assertFalse(verify(copied)["ok"])
            with self.assertRaises(ValueError):
                restore(copied, root / "second", apply=True)

    def test_refuses_backup_inside_source(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                backup([folder], Path(folder) / "nested")


if __name__ == "__main__":
    unittest.main()
