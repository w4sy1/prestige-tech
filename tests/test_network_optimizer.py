import base64
import json
from types import SimpleNamespace
import unittest

from prestige_core.network_optimizer import inspect_adapter


class NetworkOptimizerTests(unittest.TestCase):
    def test_inspection_is_read_only_and_validates_index(self):
        commands = []
        def runner(command, **kwargs):
            commands.append(command)
            return SimpleNamespace(returncode=0, stdout=json.dumps({
                "index": 7, "name": "Wi-Fi", "sections": {"dns": {"status": "OK"},
                                                    "power": {"status": "UNKNOWN"}}
            }))
        result = inspect_adapter(7, runner=runner, platform="nt")
        self.assertEqual(result["name"], "Wi-Fi")
        script = base64.b64decode(commands[0][-1]).decode("utf-16le")
        self.assertIn("Get-NetTCPSetting", script)
        self.assertNotIn("Set-DnsClientServerAddress", script)
        with self.assertRaises(ValueError):
            inspect_adapter(0, runner=runner, platform="nt")
