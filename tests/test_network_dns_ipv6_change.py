import json
import tempfile
import unittest
from pathlib import Path

from prestige_core.network_dns_ipv6_change import (
    WindowsIpv6DnsBackend, apply_ipv6_dns_change, plan_ipv6_dns_change,
    rollback_ipv6_dns_change,
)


class FakeIpv6Dns:
    def __init__(self):
        self.state = {"index": 7, "automatic": True, "servers": ["2001:db8::53"]}

    def snapshot(self, index):
        return dict(self.state)

    def set_dns(self, index, servers):
        self.state = {"index": index, "automatic": servers is None,
                      "servers": ["2001:db8::53"] if servers is None else list(servers)}


class Ipv6DnsTest(unittest.TestCase):
    def test_plan_apply_rollback_and_family_guard(self):
        backend = FakeIpv6Dns()
        self.assertTrue(plan_ipv6_dns_change(7, ["2001:4860:4860::8888"], backend)["change_needed"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "backup.json"
            self.assertEqual(apply_ipv6_dns_change(7, ["2001:4860:4860::8888"], path, backend)["status"], "APPLIED")
            self.assertEqual(json.loads(path.read_text())["operation"], "network-dns-ipv6")
            self.assertEqual(rollback_ipv6_dns_change(path, backend)["status"], "PLAN")
            backend.state["servers"] = ["2001:db8::2"]
            with self.assertRaises(RuntimeError):
                rollback_ipv6_dns_change(path, backend, apply=True)
            backend.state["servers"] = ["2001:4860:4860::8888"]
            self.assertEqual(rollback_ipv6_dns_change(path, backend, apply=True)["status"], "ROLLED_BACK")

    def test_invalid_or_duplicate_servers_rejected(self):
        for servers in (["1.1.1.1"], ["ff02::1"], ["::"], ["fe80::1%2"],
                        ["2001:db8::1", "2001:0db8::1"]):
            with self.subTest(servers=servers), self.assertRaises(ValueError):
                plan_ipv6_dns_change(7, servers, FakeIpv6Dns())

    def test_netsh_commands_limit_family_to_ipv6(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return type("Result", (), {"returncode": 0, "stdout": ""})()
        backend = object.__new__(WindowsIpv6DnsBackend)
        backend.runner = runner
        backend.set_dns(7, ["2001:db8::1", "2001:db8::2"])
        backend.set_dns(7, None)
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(command[:3] == ["netsh.exe", "interface", "ipv6"] for command in calls))
        self.assertIn("source=dhcp", calls[-1])


if __name__ == "__main__":
    unittest.main()
