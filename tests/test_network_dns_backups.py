import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.network_dns_backups import list_dns_backups


class DnsBackupCatalogTest(unittest.TestCase):
    def test_only_dns_backups_are_listed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "dns.json").write_text(json.dumps({
                "schema_version": 1, "operation": "network-dns-ipv6", "status": "APPLIED",
                "original": {"index": 8}, "created_utc": "2026-10-08T10:00:00Z",
            }), encoding="utf-8")
            (root / "other.json").write_text('{"operation":"other"}', encoding="utf-8")
            (root / "broken.json").write_text('{', encoding="utf-8")
            rows = list_dns_backups(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["family"], "ipv6")
            self.assertEqual(rows[0]["interface_index"], 8)


if __name__ == "__main__":
    unittest.main()
