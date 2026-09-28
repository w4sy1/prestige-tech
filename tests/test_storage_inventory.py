import json
import subprocess
import unittest

from prestige_core.storage_inventory import read_disks


class StorageInventoryTests(unittest.TestCase):
    def test_windows_inventory_maps_disk_and_volume_without_writes(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "Number": 3, "FriendlyName": "Test USB", "UniqueId": "fixture-3",
                "Size": 4096, "BusType": "USB", "IsReadOnly": False,
                "IsBoot": False, "IsSystem": False,
                "Partitions": {"PartitionNumber": 1, "DriveLetter": "E", "IsBoot": False, "IsSystem": False},
            }), "")
        result = read_disks(runner=runner, platform="nt")
        self.assertEqual(result[0]["device"], r"\\.\PhysicalDrive3")
        self.assertEqual(result[0]["volumes"], ["E:"])
        self.assertFalse(result[0]["system"])
        self.assertIn("Get-Disk", calls[0][-1])
        self.assertIn("Get-Partition", calls[0][-1])
        self.assertNotIn("Set-", calls[0][-1])

    def test_missing_command_is_error(self):
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, "", "failure")
        with self.assertRaises(RuntimeError):
            read_disks(runner=runner, platform="nt")


if __name__ == "__main__":
    unittest.main()
