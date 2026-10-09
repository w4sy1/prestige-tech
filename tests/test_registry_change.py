import tempfile
import json
from pathlib import Path
import unittest

from prestige_core.registry_change import rollback_file_extensions, show_file_extensions


class FakeKey:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeRegistry:
    HKEY_CURRENT_USER = object()
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_DWORD = 4

    def __init__(self):
        self.value = 1
        self.writes = []

    def OpenKey(self, hive, key, reserved, access):
        self.assert_hive = hive is self.HKEY_CURRENT_USER
        return FakeKey()

    def QueryValueEx(self, handle, name):
        return self.value, self.REG_DWORD

    def SetValueEx(self, handle, name, reserved, kind, value):
        self.writes.append(value)
        self.value = value


class RegistryChangeTests(unittest.TestCase):
    def test_backup_apply_verify_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeRegistry()
            backup = Path(directory) / "show-extensions.json"
            with self.assertRaises(ValueError):
                show_file_extensions(backup, registry=fake, platform="nt")
            self.assertEqual(fake.writes, [])
            result = show_file_extensions(backup, accept_changes=True, registry=fake, platform="nt")
            self.assertEqual(result["status"], "APPLIED")
            self.assertTrue(backup.is_file())
            self.assertEqual(json.loads(backup.read_text(encoding="utf-8"))["status"], "APPLIED")
            self.assertEqual(fake.value, 0)
            self.assertEqual(rollback_file_extensions(backup, accept_changes=True,
                                                      registry=fake, platform="nt")["status"], "ROLLED_BACK")
            self.assertEqual(fake.value, 1)
            self.assertEqual(json.loads(backup.read_text(encoding="utf-8"))["status"], "ROLLED_BACK")

    def test_no_overwrite_and_changed_value_refuses_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeRegistry()
            backup = Path(directory) / "backup.json"
            show_file_extensions(backup, accept_changes=True, registry=fake, platform="nt")
            fake.value = 1
            with self.assertRaises(ValueError):
                rollback_file_extensions(backup, accept_changes=True, registry=fake, platform="nt")
            self.assertEqual(fake.writes, [0])
            fake.value = 1
            with self.assertRaises(FileExistsError):
                show_file_extensions(backup, accept_changes=True, registry=fake, platform="nt")
            self.assertEqual(fake.writes, [0])
