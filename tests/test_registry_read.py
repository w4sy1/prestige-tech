import unittest

from prestige_core.registry_read import OPERATIONS, read_operation


class EndOfValues(OSError):
    winerror = 259


class FakeKey:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeRegistry:
    HKEY_CURRENT_USER = object()
    HKEY_LOCAL_MACHINE = object()
    KEY_READ = 0x20019

    def __init__(self, values=None, missing_key=False):
        self.values = values or {}
        self.missing_key = missing_key
        self.opens = []

    def OpenKey(self, hive, key, reserved, access):
        self.opens.append((hive, key, reserved, access))
        if self.missing_key:
            raise FileNotFoundError()
        return FakeKey()

    def QueryValueEx(self, handle, name):
        if name not in self.values:
            raise FileNotFoundError()
        return self.values[name]

    def EnumValue(self, handle, index):
        values = list(self.values.items())
        if index >= len(values):
            raise EndOfValues()
        name, (value, data_type) = values[index]
        return name, value, data_type


class RegistryReadTests(unittest.TestCase):
    def test_catalog_has_unique_documented_read_operations(self):
        self.assertEqual(len(OPERATIONS), 29)
        self.assertEqual(len({operation.id for operation in OPERATIONS}), 29)
        self.assertTrue(all(operation.source.startswith("https://learn.microsoft.com/") for operation in OPERATIONS))
        self.assertTrue(all(operation.risk == "read_only" for operation in OPERATIONS))

    def test_single_value_reads_use_only_query(self):
        for operation in OPERATIONS[5:]:
            self.assertEqual(len(operation.values), 1)
            fake = FakeRegistry({operation.values[0]: (1, 4)})
            result = read_operation(operation, registry=fake, platform="nt")
            self.assertEqual(result["status"], "OK", operation.id)
            self.assertEqual(result["rows"][0]["status"], "OK", operation.id)
            self.assertEqual(fake.opens[0][1], operation.key)
            self.assertEqual(fake.opens[0][3], fake.KEY_READ)

    def test_shell_folder_fixture_reads_without_writes(self):
        fake = FakeRegistry({"Desktop": (r"%USERPROFILE%\Desktop", 2)})
        result = read_operation(OPERATIONS[0], registry=fake, platform="nt")
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["rows"][0]["name"], "Desktop")
        self.assertEqual(result["rows"][0]["type"], 2)
        self.assertEqual(result["rows"][1]["status"], "Niedostępne")
        self.assertEqual(fake.opens[0][3], fake.KEY_READ)

    def test_missing_autorun_key_is_unavailable(self):
        result = read_operation(OPERATIONS[2], registry=FakeRegistry(missing_key=True), platform="nt")
        self.assertEqual(result["status"], "Niedostępne")

    def test_autorun_fixture_enumerates_values(self):
        fake = FakeRegistry({"Example": (r"C:\Example\app.exe", 1)})
        result = read_operation(OPERATIONS[1], registry=fake, platform="nt")
        self.assertEqual(result["rows"], [{
            "name": "Example", "value": r"C:\Example\app.exe", "type": 1, "status": "OK",
        }])

    def test_machine_autorun_uses_hklm_read_only(self):
        fake = FakeRegistry({"MachineApp": (r"C:\Example\service.exe", 1)})
        result = read_operation(OPERATIONS[3], registry=fake, platform="nt")
        self.assertEqual(result["status"], "OK")
        self.assertIs(fake.opens[0][0], fake.HKEY_LOCAL_MACHINE)
        self.assertEqual(fake.opens[0][3], fake.KEY_READ)


if __name__ == "__main__":
    unittest.main()
