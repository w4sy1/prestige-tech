import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from prestige_core.usb_readonly import set_usb_readonly


class UsbReadonlyTests(unittest.TestCase):
    @staticmethod
    def disk(**overrides):
        disk = {"number": 7, "unique_id": "USB-ID-7", "size_bytes": 8192,
                "bus": "USB", "system": False, "read_only": False}
        disk.update(overrides)
        return disk

    def test_diskpart_script_is_fixed_and_status_rechecked(self):
        states = iter([[self.disk()], [self.disk()], [self.disk(read_only=True)]])
        calls = []

        def runner(command, **kwargs):
            self.assertEqual(command[:2], ["diskpart.exe", "/s"])
            calls.append(Path(command[2]))
            self.assertEqual(calls[-1].read_text(encoding="ascii"),
                             "select disk 7\nattributes disk set readonly\n")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        result = set_usb_readonly(7, "USB-ID-7", 8192,
                                  disks_reader=lambda: next(states), runner=runner,
                                  admin_check=lambda: True, platform="nt")
        self.assertEqual(result["status"], "READ_ONLY_SET")
        self.assertFalse(calls[0].exists())

    def test_rejects_system_nonusb_and_changed_identity(self):
        for disk in (self.disk(system=True), self.disk(bus="SATA"),
                     self.disk(unique_id="OTHER"), self.disk(size_bytes=4096)):
            with self.subTest(disk=disk), self.assertRaises(ValueError):
                set_usb_readonly(7, "USB-ID-7", 8192, disks_reader=lambda: [disk],
                                 runner=lambda *_a, **_k: self.fail("DiskPart uruchomiony"),
                                 admin_check=lambda: True, platform="nt")

    def test_no_admin_and_no_verified_attribute(self):
        with self.assertRaises(PermissionError):
            set_usb_readonly(7, "USB-ID-7", 8192, disks_reader=lambda: [self.disk()],
                             admin_check=lambda: False, platform="nt")
        with self.assertRaises(RuntimeError):
            set_usb_readonly(7, "USB-ID-7", 8192, disks_reader=lambda: [self.disk()],
                             runner=lambda *_a, **_k: SimpleNamespace(returncode=0),
                             admin_check=lambda: True, platform="nt")

    def test_already_readonly_does_not_run(self):
        result = set_usb_readonly(7, "USB-ID-7", 8192,
                                  disks_reader=lambda: [self.disk(read_only=True)],
                                  runner=lambda *_a, **_k: self.fail("DiskPart uruchomiony"),
                                  admin_check=lambda: True, platform="nt")
        self.assertEqual(result["status"], "ALREADY_READ_ONLY")
