import json
from types import SimpleNamespace
import unittest

from prestige_core.usb_inventory import read_usb_devices


class UsbInventoryTests(unittest.TestCase):
    def test_vid_pid_from_present_pnp_only(self):
        rows = [{"InstanceId": "USB\\VID_1234&PID_abCD\\XYZ", "FriendlyName": "Pendrive",
                 "Class": "DiskDrive", "Status": "OK"},
                {"InstanceId": "PCI\\VEN_1234", "FriendlyName": "PCI"}]
        def runner(command, **kwargs):
            self.assertIn("-PresentOnly", command[-1])
            return SimpleNamespace(returncode=0, stdout=json.dumps(rows))
        result = read_usb_devices(runner=runner, platform="nt")
        self.assertEqual(result["count"], 1)
        self.assertEqual((result["devices"][0]["vid"], result["devices"][0]["pid"]),
                         ("1234", "ABCD"))
