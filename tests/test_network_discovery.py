import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from prestige_core.network_discovery import (load_oui, local_scopes, plan_targets,
                                             reverse_name, scan_local_scope)


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
