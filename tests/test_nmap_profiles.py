from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from prestige_core.nmap_profiles import compare_results, parse_xml, plan_profile, run_profile


XML = '<nmaprun><host><status state="up"/><address addr="127.0.0.1" addrtype="ipv4"/><ports><port protocol="tcp" portid="80"><state state="open"/></port></ports></host></nmaprun>'


class NmapProfilesTests(unittest.TestCase):
    def test_scope_and_authorization(self):
        self.assertIn("-sT", plan_profile("quick", "127.0.0.1"))
        with self.assertRaises(ValueError):
            plan_profile("quick", "192.168.1.1")
        with self.assertRaises(ValueError):
            plan_profile("quick", "192.168.0.0/16", authorized=True)
        self.assertEqual(plan_profile("lan-discovery", "192.168.1.0/24", authorized=True)[-1],
                         "192.168.1.0/24")

    def test_xml_parse_compare_and_reject_dtd(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scan.xml"
            path.write_text(XML, encoding="utf-8")
            hosts = parse_xml(path)
            self.assertEqual(hosts["127.0.0.1"]["ports"]["tcp/80"]["state"], "open")
            self.assertEqual(compare_results({}, hosts)["changes"][0]["event"], "NEW_HOST")
            path.write_text('<!DOCTYPE a><nmaprun/>', encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_xml(path)

    def test_run_creates_unique_report(self):
        with tempfile.TemporaryDirectory() as directory:
            def runner(command, **kwargs):
                xml_path = Path(command[command.index("-oX") + 1])
                xml_path.write_text(XML, encoding="utf-8")
                return SimpleNamespace(returncode=0)
            result = run_profile("quick", "127.0.0.1", directory, runner=runner)
            self.assertEqual(len(result["hosts"]), 1)
            self.assertTrue(Path(result["xml"]).is_file())
