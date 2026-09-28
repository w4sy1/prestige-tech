import json
from pathlib import Path
import tempfile
import unittest

from prestige_core.registry_transactions import (OPERATIONS, apply_change,
                                                 plan_change, rollback_change)


class FakeKey:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeRegistry:
    HKEY_CURRENT_USER = object()
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_DWORD = 4

    def __init__(self, name, value, kind=4):
        self.name, self.value, self.kind = name, value, kind
        self.writes = []
        self.fail_verify = False

    def OpenKey(self, hive, key, reserved, access):
        assert hive is self.HKEY_CURRENT_USER
        assert access in (self.KEY_READ, self.KEY_SET_VALUE)
        return FakeKey()

    def QueryValueEx(self, handle, name):
        assert name == self.name
        return self.value, self.kind

    def SetValueEx(self, handle, name, reserved, kind, value):
        assert name == self.name
        self.writes.append(value)
        if not self.fail_verify:
            self.value = value


class RegistryTransactionTests(unittest.TestCase):
    def test_each_operation_plans_and_roundtrips_without_overwrite(self):
        self.assertEqual(len(OPERATIONS), len({item.id for item in OPERATIONS}))
        with tempfile.TemporaryDirectory() as directory:
            for item in OPERATIONS:
                with self.subTest(item=item.id):
                    previous = next(value for value in item.allowed if value != item.target)
                    fake = FakeRegistry(item.name, previous)
                    path = Path(directory) / (item.id + ".json")
                    self.assertTrue(plan_change(item.id, registry=fake, platform="nt")["change_needed"])
                    self.assertEqual(fake.writes, [])
                    with self.assertRaises(ValueError):
                        apply_change(item.id, path, registry=fake, platform="nt")
                    self.assertEqual(apply_change(item.id, path, accept_changes=True,
                                                  registry=fake, platform="nt")["status"], "APPLIED")
                    self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], "APPLIED")
                    self.assertEqual(fake.value, item.target)
                    self.assertEqual(rollback_change(path, accept_changes=True,
                                                     registry=fake, platform="nt")["status"], "ROLLED_BACK")
                    self.assertEqual(fake.value, previous)
                    with self.assertRaises(ValueError):
                        rollback_change(path, accept_changes=True, registry=fake, platform="nt")

    def test_changed_value_wrong_type_and_backup_collision_refused(self):
        item = OPERATIONS[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.json"
            fake = FakeRegistry(item.name, 2)
            apply_change(item.id, path, accept_changes=True, registry=fake, platform="nt")
            fake.value = 2
            with self.assertRaises(ValueError):
                rollback_change(path, accept_changes=True, registry=fake, platform="nt")
            with self.assertRaises(FileExistsError):
                apply_change(item.id, path, accept_changes=True, registry=fake, platform="nt")
            fake.kind = 1
            with self.assertRaises(ValueError):
                plan_change(item.id, registry=fake, platform="nt")

    def test_verification_failure_restores_previous(self):
        item = OPERATIONS[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.json"
            fake = FakeRegistry(item.name, 2)
            fake.fail_verify = True
            with self.assertRaises(RuntimeError):
                apply_change(item.id, path, accept_changes=True, registry=fake, platform="nt")
            self.assertEqual(fake.value, 2)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], "ROLLED_BACK")


if __name__ == "__main__":
    unittest.main()
