import json
from pathlib import Path
import tempfile
import unittest

from prestige_core.registry_backup_store import list_backups, new_backup_path
from prestige_core.registry_transactions import OPERATIONS as CHANGES
from prestige_core.registry_policy_changes import KEY as POLICY_KEY, OPERATIONS as POLICIES


class RegistryBackupStoreTests(unittest.TestCase):
    def test_new_path_is_unique_and_does_not_create_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            first = new_backup_path(CHANGES[0].id, folder=directory)
            second = new_backup_path(CHANGES[0].id, folder=directory)
            self.assertNotEqual(first, second)
            self.assertFalse(first.exists())
            self.assertEqual(first.parent, Path(directory))
            with self.assertRaises(ValueError):
                new_backup_path("UNKNOWN", folder=directory)

    def test_inventory_accepts_only_known_backup_shape_without_values(self):
        with tempfile.TemporaryDirectory() as directory:
            change = CHANGES[0]
            path = new_backup_path(change.id, folder=directory)
            path.write_text(json.dumps({"schema_version": 1, "operation": change.id,
                                        "hive": "HKCU", "key": change.key, "name": change.name,
                                        "type": "REG_DWORD", "previous": 2,
                                        "applied": change.target, "status": "APPLIED"}), encoding="utf-8")
            policy = POLICIES[0]
            second = new_backup_path(policy.id, folder=directory)
            second.write_text(json.dumps({"schema_version": 2, "operation": policy.id,
                                          "hive": "HKCU", "key": POLICY_KEY,
                                          "name": policy.name, "type": "REG_DWORD",
                                          "key_existed": False, "previous": None,
                                          "applied": 1, "status": "APPLIED"}), encoding="utf-8")
            invalid = new_backup_path(policy.id, folder=directory)
            invalid.write_text('{"operation":"REG-WRITE-012","key":"wrong"}', encoding="utf-8")
            rows = list_backups(folder=directory)
            self.assertEqual({item["operation"] for item in rows}, {change.id, policy.id})
            self.assertEqual(len(rows), 2)
            self.assertNotIn("previous", str(rows))

    def test_missing_directory_is_empty_and_large_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            absent = Path(directory) / "missing"
            self.assertEqual(list_backups(folder=absent), [])
            path = new_backup_path(CHANGES[0].id, folder=directory)
            path.write_bytes(b"x" * 65537)
            self.assertEqual(list_backups(folder=directory), [])


if __name__ == "__main__":
    unittest.main()
