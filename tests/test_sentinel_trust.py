import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.sentinel_trust import change_trust, rollback_trust


class SentinelTrustTest(unittest.TestCase):
    def test_add_remove_and_conditional_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            known = root / "known-devices.json"
            trusted = root / "trusted-devices.json"
            known.write_text(json.dumps([{"Key": "device-1", "IP": "192.0.2.1",
                                          "MAC": "aa:bb:cc:dd:ee:ff", "Name": "Test"}]), encoding="utf-8")
            trusted.write_text("[]", encoding="utf-8")
            first = change_trust(known, trusted, "device-1", True)
            self.assertEqual(first["status"], "APPLIED")
            self.assertEqual(json.loads(trusted.read_text())[0]["Key"], "device-1")
            self.assertEqual(change_trust(known, trusted, "device-1", True)["status"], "UNCHANGED")
            second = change_trust(known, trusted, "device-1", False)
            self.assertEqual(json.loads(trusted.read_text()), [])
            with self.assertRaises(RuntimeError):
                rollback_trust(trusted, first["backup"])
            self.assertEqual(rollback_trust(trusted, second["backup"])["status"], "ROLLED_BACK")
            self.assertEqual(json.loads(trusted.read_text())[0]["Key"], "device-1")

    def test_unknown_device_and_corrupt_list_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            known, trusted = root / "known.json", root / "trusted.json"
            known.write_text('[{"Key":"one"}]', encoding="utf-8")
            trusted.write_text('[]', encoding="utf-8")
            with self.assertRaises(ValueError):
                change_trust(known, trusted, "two", True)
            trusted.write_text('[{}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                change_trust(known, trusted, "one", True)


if __name__ == "__main__":
    unittest.main()
