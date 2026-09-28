import tempfile
from pathlib import Path
import unittest

from prestige_core.device_history import DeviceHistory, normalize_devices


class DeviceHistoryTests(unittest.TestCase):
    def test_multi_ip_and_events_without_offline_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "devices.sqlite"
            store = DeviceHistory(path)
            first = [{"mac": "AA-BB-CC-DD-EE-02", "ips": ["192.168.1.2"]}]
            self.assertEqual(store.observe(first)["events"][0]["event"], "NEW_DEVICE")
            self.assertEqual(store.observe(first)["events"], [])
            self.assertEqual(store.observe([])["events"], [])
            self.assertEqual(store.devices()[0]["status"], "observed")
            changed = [{"mac": "aa:bb:cc:dd:ee:02", "ips": ["192.168.1.2", "192.168.1.3"]}]
            self.assertEqual(store.observe(changed)["events"][0]["event"], "IP_CHANGE")
            self.assertEqual(store.devices()[0]["ips"], ["192.168.1.2", "192.168.1.3"])
            store.close()
            reopened = DeviceHistory(path)
            self.assertEqual(len(reopened.history()), 2)
            reopened.close()

    def test_complete_observation_says_not_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = DeviceHistory(Path(directory) / "devices.sqlite")
            store.observe([{"mac": "aa:bb:cc:dd:ee:02", "ips": ["192.168.1.2"]}])
            result = store.observe([], complete=True)
            self.assertEqual(result["events"][0]["event"], "NOT_OBSERVED")
            self.assertEqual(store.devices()[0]["status"], "not_observed")
            store.close()

    def test_rejects_multicast_mac(self):
        with self.assertRaises(ValueError):
            normalize_devices([{"mac": "01:00:5e:00:00:01", "ips": ["192.168.1.1"]}])

    def test_tag_persists_across_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            store = DeviceHistory(Path(directory) / "devices.sqlite")
            row = {"mac": "00:11:22:33:44:55", "ips": ["192.0.2.5"]}
            store.observe([row])
            store.tag_device(row["mac"], "IoT")
            store.observe([row])
            self.assertEqual(store.devices()[0]["category"], "IoT")
            with self.assertRaises(ValueError):
                store.tag_device(row["mac"], "Nieznana kategoria")
            store.close()
