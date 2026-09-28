import json
import subprocess
import unittest

from prestige_core.security_check import CHECKS, audit_windows, collect, load_evidence
from prestige_core.security_rules import audit, CHECK_NAMES


class SecurityCheckTests(unittest.TestCase):
    def test_all_legacy_categories_and_unknown_coverage(self):
        self.assertEqual(set(CHECKS), set(CHECK_NAMES))
        report = audit({"defender": {"status": "OK", "data": [
            {"AntivirusEnabled": False, "RealTimeProtectionEnabled": False}]}})
        self.assertEqual(report["coverage"]["defender"], "EVALUATED")
        self.assertEqual(report["coverage"]["firewall"], "UNKNOWN")
        self.assertGreater(report["risk_score"], 0)
        self.assertFalse(report["ok"])

    def test_collector_preserves_unknown_when_one_check_fails(self):
        payload = {name: {"status": "UNKNOWN", "error": "AccessDenied", "data": []}
                   for name in CHECK_NAMES}
        def runner(command, **kwargs):
            self.assertIn("-EncodedCommand", command)
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        report = audit_windows(runner=runner, platform="nt")
        self.assertEqual(report["unknown_checks"], len(CHECK_NAMES))
        self.assertEqual(report["risk_score"], 0)
        self.assertFalse(report["ok"])

    def test_non_windows_rejected(self):
        with self.assertRaises(RuntimeError):
            collect(platform="posix")

    def test_offline_evidence_has_size_limit(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checks.json"
            path.write_text('{"defender": {"status": "UNKNOWN", "data": []}}', encoding="utf-8")
            self.assertEqual(load_evidence(path)["defender"]["status"], "UNKNOWN")
            with self.assertRaises(ValueError):
                load_evidence(path, max_bytes=1)
