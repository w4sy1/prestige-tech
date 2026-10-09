import tempfile
import unittest
from pathlib import Path

from prestige_core.network_report import export_network_report


class NetworkReportTest(unittest.TestCase):
    def test_escapes_observations_and_explains_cache(self):
        discovery = {"status": "UNKNOWN", "scope": "192.168.1.0/24", "observed": [
            {"ip": "192.168.1.2", "mac": "", "hostname": "<script>",
             "evidence": "Cache — dostępność nieznana"}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.html"
            export_network_report(discovery, None, path)
            contents = path.read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;", contents)
            self.assertNotIn("<script>", contents)
            self.assertIn("nie dowodzi obecności", contents)
            with self.assertRaises(FileExistsError):
                export_network_report(discovery, None, path)


if __name__ == "__main__":
    unittest.main()
