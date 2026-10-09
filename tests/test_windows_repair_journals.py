import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.windows_repairs import list_repair_journals


class RepairJournalListTest(unittest.TestCase):
    def test_lists_metadata_without_snapshot_or_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prestige-repair-example.json"
            path.write_text(json.dumps({"schema_version": 1, "operation": "sfc",
                                        "status": "COMPLETE", "snapshot": {"private": "data"},
                                        "output_tail": "private"}), encoding="utf-8")
            rows = list_repair_journals(folder)
            self.assertEqual(len(rows), 1)
            self.assertNotIn("snapshot", rows[0])
            self.assertNotIn("output_tail", rows[0])


if __name__ == "__main__":
    unittest.main()
