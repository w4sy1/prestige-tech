import unittest
from unittest.mock import Mock

from prestige_core.system_help_checks import read_audio_devices, read_printer_state


class SystemHelpCheckTests(unittest.TestCase):
    def test_printer_read_preserves_service_and_counts_without_document_names(self):
        probe = Mock(return_value={"status": "COMPLETE", "service": "Running",
                                   "printers": [{"name": "Office", "job_count": 2}],
                                   "error_type": None})
        result = read_printer_state(platform="nt", powershell=probe)
        self.assertEqual(result["printers"][0]["job_count"], 2)
        self.assertFalse(result["system_changed"])
        self.assertNotIn("document", str(result).lower())
        self.assertIn("Get-Service", probe.call_args.args[0])

    def test_audio_inventory_does_not_claim_to_know_mute(self):
        probe = Mock(return_value={"status": "COMPLETE", "devices": [
            {"name": "Speakers", "status": "OK", "error_code": 0}]})
        result = read_audio_devices(platform="nt", powershell=probe)
        self.assertEqual(result["mute"], "UNKNOWN")
        self.assertEqual(result["default_output"], "UNKNOWN")
        self.assertFalse(result["system_changed"])

    def test_non_windows_rejected_without_calling_powershell(self):
        probe = Mock()
        with self.assertRaises(RuntimeError):
            read_printer_state(platform="posix", powershell=probe)
        probe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
