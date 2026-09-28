import json
import tempfile
from pathlib import Path
import unittest

from prestige_core.baseline_update import update_baseline
from prestige_core.file_snapshot import scan_files


class BaselineUpdateTests(unittest.TestCase):
    def test_requires_acceptance_and_preserves_previous_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "a.txt").write_text("old", encoding="utf-8")
            first = scan_files(root)
            target = Path(directory) / "baseline.json"
            target.write_text(json.dumps(first), encoding="utf-8")
            (root / "a.txt").write_text("new", encoding="utf-8")
            current = scan_files(root)
            plan = update_baseline(target, current)
            self.assertFalse(plan["updated"])
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), first)
            result = update_baseline(target, current, accept_changes=True)
            self.assertTrue(result["updated"])
            self.assertEqual(json.loads(Path(result["backup"]).read_text(encoding="utf-8")), first)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), current)

    def test_rejects_incomplete_scan_and_baseline_inside_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            current = scan_files(root)
            target = root / "baseline.json"
            target.write_text(json.dumps(current), encoding="utf-8")
            with self.assertRaises(ValueError):
                update_baseline(target, current, accept_changes=True)
            outside = Path(directory) / "outside.json"
            outside.write_text(json.dumps(current), encoding="utf-8")
            current["complete"] = False
            with self.assertRaises(ValueError):
                update_baseline(outside, current, accept_changes=True)
            self.assertFalse(list(Path(directory).glob("*.bak")))


if __name__ == "__main__":
    unittest.main()
