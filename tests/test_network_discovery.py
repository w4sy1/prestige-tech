import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from prestige_core.network_discovery import (load_oui, local_scopes, plan_targets,
                                             reverse_name, scan_local_scope, nmap_discover)


class NetworkDiscoveryTests(unittest.TestCase):
    def test_scopes_cap_wide_subnet_and_exclude_public(self):
        rows = [{"IPAddress": "192.168.10.23", "PrefixLength": 16,
                 "InterfaceAlias": "Wi-Fi", "InterfaceIndex": 4},
                {"IPAddress": "8.8.8.8", "PrefixLength": 24,
                 "InterfaceAlias": "Other", "InterfaceIndex": 5}]
        def runner(*args, **kwargs):
            return SimpleNamespace(returncode=0, stdout=json.dumps(rows))
        scopes = local_scopes(runner=runner, platform="nt")
        self.assertEqual(scopes[0]["scope"], "192.168.10.0/24")
        self.assertTrue(scopes[0]["capped"])
        self.assertEqual(len(scopes), 1)

    def test_only_local_private_24_and_bounded_results(self):
        self.assertEqual(len(plan_targets("192.168.1.0/24", "192.168.1.2")), 253)
        with self.assertRaises(ValueError):
            plan_targets("8.8.8.0/24", "8.8.8.8")
        with self.assertRaises(ValueError):
            plan_targets("192.168.0.0/16", "192.168.1.2")
        def ping(command, **kwargs):
            return SimpleNamespace(returncode=0 if command[-1] == "192.168.1.3" else 1)
        result = scan_local_scope("192.168.1.0/29", "192.168.1.2", ping_runner=ping,
                                  neighbors_reader=lambda: [{"mac": "aa:bb:cc:dd:ee:ff", "ips": ["192.168.1.3"]}],
                                  max_workers=2)
        self.assertEqual(result["responsive"], [{"ip": "192.168.1.3", "mac": "aa:bb:cc:dd:ee:ff",
                                                 "hostname": "", "vendor": "Adres lokalny/losowy — producent nieznany"}])
        self.assertEqual(result["probed"], 5)
        self.assertEqual(result["status"], "COMPLETE")

    def test_neighbor_without_icmp_is_observation_not_online(self):
        def ping(*_args, **_kwargs):
            return SimpleNamespace(returncode=1)
        result = scan_local_scope(
            "192.168.1.0/29", "192.168.1.2", ping_runner=ping,
            neighbors_reader=lambda: [
                {"mac": "00:11:22:33:44:55", "ips": ["192.168.1.3", "198.51.100.2"]}],
            max_workers=2)
        self.assertEqual(result["responsive"], [])
        self.assertEqual([(row["ip"], row["evidence"]) for row in result["observed"]],
                         [("192.168.1.3", "Cache — dostępność nieznana")])

    def test_oui_and_reverse_dns_are_optional_and_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "oui.json"
            path.write_text('{"00:11:22":"Example Vendor"}', encoding="utf-8")
            oui = load_oui(path)
            def ping(command, **kwargs):
                return SimpleNamespace(returncode=0 if command[-1] == "192.168.1.3" else 1)
            result = scan_local_scope("192.168.1.0/29", "192.168.1.2", ping_runner=ping,
                                      neighbors_reader=lambda: [{"mac": "00:11:22:33:44:55",
                                                                 "ips": ["192.168.1.3"]}],
                                      oui=oui, resolve_names=True,
                                      name_resolver=lambda ip: "host.example", max_workers=2)
            self.assertEqual(result["responsive"][0]["vendor"], "Example Vendor")
            self.assertEqual(result["responsive"][0]["hostname"], "host.example")
            path.write_text('{"ZZ:11:22":"Bad"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_oui(path)

    def test_reverse_name_invokes_bounded_process(self):
        def runner(command, **kwargs):
            self.assertEqual(kwargs["timeout"], 3)
            self.assertEqual(command[-1], "192.0.2.1")
            return SimpleNamespace(returncode=0, stdout="host.example\n")
        self.assertEqual(reverse_name("192.0.2.1", runner=runner), "host.example")

    def test_nmap_discovery_is_local_and_separate_from_icmp(self):
        def nmap(command, **kwargs):
            self.assertEqual(command[1:], ["-sn", "-n", "--max-retries", "1", "192.168.1.0/29"])
            self.assertEqual(kwargs["timeout"], 45)
            return SimpleNamespace(returncode=0, stdout=(
                "Nmap scan report for 192.168.1.3\n"
                "Nmap scan report for 198.51.100.2\n"))
        found = nmap_discover("192.168.1.0/29", "192.168.1.2", runner=nmap,
                              executable="nmap-test")
        self.assertEqual(found, ["192.168.1.3"])
        result = scan_local_scope("192.168.1.0/29", "192.168.1.2",
                                  ping_runner=lambda *_a, **_kw: SimpleNamespace(returncode=1),
                                  neighbors_reader=lambda: [], use_nmap=True,
                                  nmap_runner=nmap, nmap_executable="nmap-test", max_workers=2)
        self.assertEqual(result["responsive"], [])
        self.assertEqual(result["observed"][0]["evidence"], "Nmap")
        with self.assertRaises(ValueError):
            nmap_discover("198.51.100.0/24", "198.51.100.2", runner=nmap,
                          executable="nmap-test")
