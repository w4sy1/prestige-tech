import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.report_attachments import attachment_manifest
from prestige_core.report_service import missing_fields, template


class ReportAttachmentsTest(unittest.TestCase):
    def test_manifest_records_hash_without_copying_file(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "evidence.txt"
            source.write_bytes(b"example")
            manifest = Path(folder) / "attachments.json"
            attachment_manifest([source], manifest)
            row = json.loads(manifest.read_text(encoding="utf-8"))["attachments"][0]
            self.assertEqual(row["sha256"], hashlib.sha256(b"example").hexdigest())
            self.assertEqual(row["name"], source.name)
            self.assertEqual(source.read_bytes(), b"example")

    def test_required_field_preview(self):
        missing = missing_fields(template())
        self.assertIn("Klient", missing)
        self.assertIn("Test końcowy", missing)


if __name__ == "__main__":
    unittest.main()
