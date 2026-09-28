import unittest

from prestige_core.android_adb import (inspect_apps, list_devices, logcat_summary,
                                       parse_admins, parse_appops, parse_battery,
                                       parse_devices, parse_package, read_diagnostic,
                                       require_device)


class FakeAdb:
    def __init__(self):
        self.commands = []

    def run(self, args, **_):
        self.commands.append(args)
        if args == ["devices", "-l"]:
            return "List of devices attached\nSERIAL1 device product:x\nSERIAL2 unauthorized\n"
        if args[-4:] == ["pm", "list", "packages", "-3"]:
            return "package:com.example.app\n"
        if args[-3:] == ["dumpsys", "package", "com.example.app"]:
            return "versionName=1.2\nrequested permissions:\n  android.permission.SYSTEM_ALERT_WINDOW\n"
        if args[-3:] == ["appops", "get", "com.example.app"]:
            return "SYSTEM_ALERT_WINDOW: allow"
        if args[-2:] == ["dumpsys", "battery"]:
            return "level: 50\ntemperature: 325\n"
        return "value\n"


class AndroidAdbTest(unittest.TestCase):
    def test_devices_and_authorization(self):
        devices = parse_devices("List of devices attached\nX device\nY unauthorized\n")
        self.assertEqual(require_device(None, devices), "X")
        with self.assertRaises(ValueError):
            require_device("Y", devices)
        self.assertEqual(len(list_devices(FakeAdb())), 2)

    def test_diagnostic_is_read_only_and_battery_parsed(self):
        backend = FakeAdb()
        result = read_diagnostic("SERIAL1", backend)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["results"]["battery"]["data"]["temperature_c"], 32.5)
        self.assertTrue(all("install" not in command and "uninstall" not in command
                            for command in backend.commands))
        self.assertEqual(parse_battery("bad"), {"temperature_c": None})

    def test_inspector_parses_permissions_without_malware_claim(self):
        backend = FakeAdb()
        result = inspect_apps("SERIAL1", backend)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["apps"][0]["version"], "1.2")
        self.assertEqual(result["apps"][0]["special_indicators"], ["overlay"])
        self.assertEqual(result["apps"][0]["active_special_access"], ["overlay"])
        self.assertIn("nie dowodzi", result["apps"][0]["note"])
        with self.assertRaises(ValueError):
            parse_package("bad;command", "")

    def test_logcat_summary_never_stores_message(self):
        text = "09-28 10:20:30.000 100 101 E Example: token=must-not-store"
        result = logcat_summary(text)
        self.assertEqual(result["total_errors"], 1)
        self.assertFalse(result["messages_stored"])
        self.assertNotIn("must-not-store", str(result))
        self.assertIsNone(parse_appops("SYSTEM_ALERT_WINDOW: default")["overlay"]["active"])
        self.assertEqual(parse_admins("Active admin ComponentInfo{com.example.admin/.Receiver}"),
                         {"com.example.admin"})
