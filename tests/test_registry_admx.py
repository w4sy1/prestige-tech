from pathlib import Path
import tempfile
import unittest

from prestige_core.registry_admx import load_admx_catalog
from prestige_core.registry_read import read_operation
from tests.test_registry_read import FakeRegistry


XML = """<?xml version='1.0' encoding='utf-8'?>
<policyDefinitions><policies>
<policy name='First' class='User' key='Software\\Vendor\\Policy' valueName='Feature' />
<policy name='Duplicate' class='User' key='software\\vendor\\policy' valueName='feature' />
<policy name='BothScopes' class='Both' key='Software\\Vendor\\Other' valueName='Flag' />
<policy name='NoDirectValue' class='Machine' key='Software\\Vendor\\Other' />
</policies></policyDefinitions>"""


class AdmxCatalogTests(unittest.TestCase):
    def test_unique_direct_policies_and_both_hives(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "example.admx").write_text(XML, encoding="utf-8")
            result = load_admx_catalog(directory)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(len(result["operations"]), 2)
            user, both = result["operations"]
            self.assertEqual(user.hive, "HKCU")
            self.assertEqual(both.hive, "BOTH")
            fake = FakeRegistry({"Flag": (1, 4)})
            observed = read_operation(both, registry=fake, platform="nt",
                                      catalog=result["operations"])
            self.assertEqual(observed["status"], "OK")
            self.assertEqual([row["name"] for row in observed["rows"]],
                             ["HKCU: Flag", "HKLM: Flag"])

    def test_utf16_and_bad_template_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "utf16.admx").write_text(XML.replace("utf-8", "unicode"), encoding="utf-16")
            Path(directory, "broken.admx").write_text("<policyDefinitions>", encoding="utf-8")
            result = load_admx_catalog(directory)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(len(result["operations"]), 2)
            self.assertEqual(result["errors"][0]["file"], "broken.admx")


if __name__ == "__main__":
    unittest.main()
