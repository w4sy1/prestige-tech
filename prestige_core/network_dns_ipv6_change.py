"""Zmiana wyłącznie DNS IPv6 z kopią i warunkowym cofnięciem."""

import ipaddress
import os
import subprocess

from prestige_core import network_dns_change as transaction


def _servers(values):
    if values is None:
        return None
    if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= 4:
        raise ValueError("Podaj 1–4 adresy DNS IPv6 albo tryb automatyczny.")
    result = []
    for value in values:
        address = ipaddress.IPv6Address(value)
        if address.is_unspecified or address.is_multicast or address.is_link_local:
            raise ValueError("Serwer DNS IPv6 musi być adresem unicast bez strefy.")
        normalized = str(address)
        if '%' in str(value) or normalized in result:
            raise ValueError("Nieprawidłowy lub powtórzony serwer DNS IPv6.")
        result.append(normalized)
    return result


def _state(row):
    if (not isinstance(row, dict) or type(row.get("index")) is not int
            or type(row.get("automatic")) is not bool
            or not isinstance(row.get("servers"), list)):
        raise RuntimeError("Niepełny odczyt konfiguracji DNS IPv6.")
    return {"index": transaction._index(row["index"]), "automatic": row["automatic"],
            "servers": [str(ipaddress.IPv6Address(value)) for value in row["servers"]]}


def plan_ipv6_dns_change(index, servers, backend):
    return transaction._plan_dns_change(index, servers, backend, _servers, _state)


def apply_ipv6_dns_change(index, servers, backup_path, backend):
    return transaction._apply_dns_change(index, servers, backup_path, backend,
                                         _servers, _state, "network-dns-ipv6")


def rollback_ipv6_dns_change(backup_path, backend, *, apply=False):
    return transaction._rollback_dns_change(backup_path, backend, apply=apply,
                                            state=_state, operation="network-dns-ipv6")


class WindowsIpv6DnsBackend(transaction.WindowsDnsBackend):
    """Odczyt IPv6 przez DNS Client; zapis rodziny IPv6 przez netsh."""

    def snapshot(self, index):
        index = transaction._index(index)
        script = ("[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
                  "$ErrorActionPreference='Stop';"
                  f"$a=Get-NetAdapter -InterfaceIndex {index} -ErrorAction Stop;"
                  "$key='HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip6\\Parameters\\Interfaces\\'+$a.InterfaceGuid;"
                  "$p=Get-ItemProperty -LiteralPath $key -ErrorAction Stop;"
                  f"$d=Get-DnsClientServerAddress -InterfaceIndex {index} -AddressFamily IPv6 -ErrorAction Stop;"
                  f"[pscustomobject]@{{index={index};automatic=[string]::IsNullOrWhiteSpace($p.NameServer);"
                  "servers=@($d.ServerAddresses)}|ConvertTo-Json -Depth 4 -Compress")
        return self._run(script)

    def set_dns(self, index, servers):
        index = transaction._index(index)
        servers = _servers(servers)
        commands = (["set", "dnsservers", f"name={index}", "source=dhcp"] if servers is None else
                    ["set", "dnsservers", f"name={index}", "source=static",
                     f"address={servers[0]}", "validate=no"])
        self._netsh(commands)
        if servers:
            for position, address in enumerate(servers[1:], start=2):
                self._netsh(["add", "dnsservers", f"name={index}", f"address={address}",
                             f"index={position}", "validate=no"])

    def _netsh(self, command):
        try:
            result = self.runner(["netsh.exe", "interface", "ipv6", *command],
                                 capture_output=True, text=True, encoding="utf-8",
                                 timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError("Polecenie DNS IPv6 nie zostało wykonane.") from error
        if result.returncode:
            raise RuntimeError("Zmiana DNS IPv6 nie powiodła się; sprawdź uprawnienia administratora.")
