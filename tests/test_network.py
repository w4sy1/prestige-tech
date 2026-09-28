import json
import subprocess
import unittest

from prestige_core.network import normalize_neighbors, read_adapters, read_neighbors


class NetworkTests(unittest.TestCase):
    def test_normalize_merges_ips_and_excludes_invalid_macs(self):
        rows = [
            {"ip": "192.168.1.20", "mac": "A0-B1-C2-D3-E4-F5", "state": "Reachable"},
            {"ip": "192.168.1.8", "mac": "a0:b1:c2:d3:e4:f5", "state": "Stale"},
            {"ip": "192.168.1.9", "mac": "ff:ff:ff:ff:ff:ff"},
        ]
        actual = normalize_neighbors(rows)
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0]["ips"], ["192.168.1.8", "192.168.1.20"])
        self.assertEqual(actual[0]["states"], ["Reachable", "Stale"])

    def test_windows_read_only_command_and_single_row(self):
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "IPAddress": "10.0.0.3", "LinkLayerAddress": "a0-b1-c2-d3-e4-f5",
                "State": "Stale", "InterfaceIndex": 7,
            }), "")
        actual = read_neighbors(runner=runner, platform="nt")
        self.assertEqual(actual[0]["ips"], ["10.0.0.3"])
        self.assertEqual(calls[0][0][0], "powershell.exe")
        self.assertIn("Get-NetNeighbor", calls[0][0][-1])
        self.assertNotIn("ping", " ".join(calls[0][0]).lower())

    def test_failed_read_is_error_not_empty_success(self):
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, "", "failure")
        with self.assertRaises(RuntimeError):
            read_neighbors(runner=runner, platform="nt")

    def test_adapter_read_normalizes_single_row_and_uses_read_only_commands(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "InterfaceAlias": "Ethernet", "InterfaceIndex": 4,
                "IPv4": "192.0.2.4", "Gateway": ["192.0.2.1"],
                "Dns": ["9.9.9.9", "not-an-ip"],
            }), "")
        self.assertEqual(read_adapters(runner=runner, platform="nt"), [{
            "name": "Ethernet", "index": 4, "ipv4": ["192.0.2.4"],
            "gateway": ["192.0.2.1"], "dns": ["9.9.9.9"],
        }])
        self.assertIn("Get-NetIPConfiguration", calls[0][-1])
        self.assertIn("Get-DnsClientServerAddress", calls[0][-1])
        self.assertNotIn("Set-", calls[0][-1])

    def test_adapter_error_is_not_empty_success(self):
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, "", "failure")
        with self.assertRaises(RuntimeError):
            read_adapters(runner=runner, platform="nt")


if __name__ == "__main__":
    unittest.main()
