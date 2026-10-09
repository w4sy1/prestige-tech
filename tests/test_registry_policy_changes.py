import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from prestige_core.registry_policy_changes import (
    KEY, OPERATIONS, _check_host_support, apply_policy_change, plan_policy_change,
    preview_policy_rollback, rollback_policy_change,
)


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

    def __init__(self, *, key_exists=False, initial=None):
        self.key_exists = key_exists
        self.values = dict(initial or {})
        self.fail_write = False

    def OpenKey(self, hive, key, reserved, access):
        assert hive is self.HKEY_CURRENT_USER and key == KEY
        if not self.key_exists:
            raise FileNotFoundError
        return FakeKey()

    def CreateKeyEx(self, hive, key, reserved, access):
        assert hive is self.HKEY_CURRENT_USER and key == KEY
        self.key_exists = True
        return FakeKey()

    def QueryValueEx(self, handle, name):
        if name not in self.values:
            raise FileNotFoundError
        return self.values[name]

    def SetValueEx(self, handle, name, reserved, kind, value):
        if not self.fail_write:
            self.values[name] = (value, kind)

    def DeleteValue(self, handle, name):
        if name not in self.values:
            raise FileNotFoundError
        del self.values[name]

    def DeleteKey(self, hive, key):
        assert hive is self.HKEY_CURRENT_USER and key == KEY
        if self.values:
            raise OSError("Klucz niepusty")
        self.key_exists = False


class PolicyChangeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Sprawdzenie winreg wymaga Windows")
    def test_unsupported_edition_requires_explicit_experimental_mode(self):
        import winreg
        with (patch("prestige_core.registry_policy_changes.sys.getwindowsversion",
                    return_value=SimpleNamespace(build=26100)),
              patch.object(winreg, "OpenKey", return_value=FakeKey()),
              patch.object(winreg, "QueryValueEx", return_value=("Core", winreg.REG_SZ))):
            with self.assertRaises(RuntimeError):
                _check_host_support(None, "nt")
            self.assertFalse(_check_host_support(None, "nt", allow_unsupported=True))

    def test_each_policy_roundtrip_absent_key_and_existing_zero(self):
        self.assertEqual(len(OPERATIONS), len({item.id for item in OPERATIONS}))
        with tempfile.TemporaryDirectory() as directory:
            for item in OPERATIONS:
                for exists in (False, True):
                    with self.subTest(item=item.id, key_existed=exists):
                        initial = {item.name: (0, 4)} if exists else None
                        fake = FakeRegistry(key_exists=exists, initial=initial)
                        path = Path(directory) / f"{item.id}-{exists}.json"
                        plan = plan_policy_change(item.id, registry=fake, platform="nt")
                        self.assertTrue(plan["change_needed"])
                        self.assertEqual(plan["current"], 0 if exists else None)
                        with self.assertRaises(ValueError):
                            apply_policy_change(item.id, path, registry=fake, platform="nt")
                        self.assertFalse(path.exists())
                        result = apply_policy_change(item.id, path, accept_changes=True,
                                                     registry=fake, platform="nt")
                        self.assertEqual(result["status"], "APPLIED")
                        self.assertEqual(fake.values[item.name], (1, 4))
                        self.assertEqual(preview_policy_rollback(path, registry=fake,
                                                                  platform="nt")["status"], "PLAN")
                        self.assertEqual(rollback_policy_change(path, accept_changes=True,
                                                                 registry=fake, platform="nt")["status"],
                                         "ROLLED_BACK")
                        self.assertEqual(fake.key_exists, exists)
                        self.assertEqual(fake.values, initial or {})
                        with self.assertRaises(ValueError):
                            rollback_policy_change(path, accept_changes=True,
                                                   registry=fake, platform="nt")

    def test_conflict_wrong_type_and_backup_collision(self):
        item = OPERATIONS[0]
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeRegistry(key_exists=True, initial={item.name: (0, 4)})
            path = Path(directory) / "backup.json"
            apply_policy_change(item.id, path, accept_changes=True, registry=fake,
                                platform="nt")
            fake.values[item.name] = (0, 4)
            self.assertEqual(preview_policy_rollback(path, registry=fake,
                                                     platform="nt")["status"], "REFUSED")
            with self.assertRaises(ValueError):
                rollback_policy_change(path, accept_changes=True, registry=fake,
                                       platform="nt")
            with self.assertRaises(FileExistsError):
                apply_policy_change(item.id, path, accept_changes=True, registry=fake,
                                    platform="nt")
            fake.values[item.name] = ("bad", 1)
            with self.assertRaises(ValueError):
                plan_policy_change(item.id, registry=fake, platform="nt")
            record = json.loads(path.read_text(encoding="utf-8"))
            record["name"] = "other"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(ValueError):
                preview_policy_rollback(path, registry=fake, platform="nt")

    def test_failed_write_keeps_recovery_record(self):
        item = OPERATIONS[0]
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeRegistry()
            fake.fail_write = True
            path = Path(directory) / "backup.json"
            with self.assertRaises(RuntimeError):
                apply_policy_change(item.id, path, accept_changes=True, registry=fake,
                                    platform="nt")
            self.assertFalse(fake.key_exists)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"],
                             "ROLLED_BACK")

    def test_external_change_before_write_is_never_overwritten(self):
        item = OPERATIONS[0]

        class ConcurrentRegistry(FakeRegistry):
            reads = 0

            def QueryValueEx(self, handle, name):
                self.reads += 1
                if self.reads == 2:
                    self.values[name] = (1, self.REG_DWORD)
                return super().QueryValueEx(handle, name)

        with tempfile.TemporaryDirectory() as directory:
            fake = ConcurrentRegistry(key_exists=True, initial={item.name: (0, 4)})
            path = Path(directory) / "backup.json"
            with self.assertRaises(RuntimeError):
                apply_policy_change(item.id, path, accept_changes=True,
                                    registry=fake, platform="nt")
            self.assertEqual(fake.values[item.name], (1, 4))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"],
                             "ABORTED_CONFLICT")


if __name__ == "__main__":
    unittest.main()
