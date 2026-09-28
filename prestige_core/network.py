"""Wspólny, wyłącznie odczytowy odczyt lokalnej tablicy sąsiadów."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess


def normalize_neighbors(rows):
    """Scal IPv4 tego samego MAC bez zgadywania statusu urządzenia."""
    if not isinstance(rows, list):
        raise ValueError("Wymagana lista wpisów sąsiadów.")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            address = ipaddress.ip_address(row["ip"])
            mac = str(row["mac"]).lower().replace("-", ":")
            if address.version != 4 or not re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", mac):
                continue
            if mac == "00:00:00:00:00:00" or int(mac[:2], 16) & 1:
                continue
            entry = result.setdefault(mac, {"mac": mac, "ips": [], "states": [], "interfaces": []})
            if str(address) not in entry["ips"]:
                entry["ips"].append(str(address))
            state = str(row.get("state") or "Nieznany")
            if state not in entry["states"]:
                entry["states"].append(state)
            interface = row.get("interface_index")
            if interface is not None and str(interface) not in entry["interfaces"]:
                entry["interfaces"].append(str(interface))
        except (KeyError, ValueError, TypeError):
            continue
    for entry in result.values():
        entry["ips"].sort(key=lambda value: int(ipaddress.ip_address(value)))
        entry["states"].sort()
        entry["interfaces"].sort()
    return sorted(result.values(), key=lambda item: item["ips"][0])


def read_neighbors(*, runner=subprocess.run, platform=None):
    """Odczytaj cache ARP/NDP; nie wykonuj ping ani skanu sieci."""
    platform = platform or os.name
    if platform == "nt":
        command = [
            "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
            "@(Get-NetNeighbor -AddressFamily IPv4 -ErrorAction Stop | "
            "Select-Object IPAddress,LinkLayerAddress,@{Name='State';Expression={$_.State.ToString()}},InterfaceIndex) | ConvertTo-Json -Compress",
        ]
    else:
        command = ["ip", "-j", "neigh"]
    try:
        proc = runner(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Odczyt tablicy sąsiadów jest niedostępny: {error}") from error
    if proc.returncode:
        raise RuntimeError("Nie udało się odczytać tablicy sąsiadów. Sprawdź narzędzie systemowe i uprawnienia.")
    try:
        raw = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as error:
        raise RuntimeError("System zwrócił nieprawidłowe dane sąsiadów.") from error
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raise RuntimeError("Nieprawidłowy format danych sąsiadów.")
    if platform == "nt":
        rows = [{"ip": row.get("IPAddress"), "mac": row.get("LinkLayerAddress"),
                 "state": row.get("State"), "interface_index": row.get("InterfaceIndex")}
                for row in raw if isinstance(row, dict)]
    else:
        rows = [{"ip": row.get("dst"), "mac": row.get("lladdr"),
                 "state": row.get("state"), "interface_index": row.get("dev")}
                for row in raw if isinstance(row, dict)]
    return normalize_neighbors(rows)


def read_adapters(*, runner=subprocess.run, platform=None):
    """Odczytaj konfigurację adapterów Windows bez zmiany ustawień DNS/IP."""
    platform = platform or os.name
    if platform != "nt":
        raise RuntimeError("Odczyt konfiguracji adapterów jest obecnie dostępny tylko w Windows.")
    script = (
        "@(Get-NetIPConfiguration -ErrorAction Stop | ForEach-Object { "
        "$item=$_; $dns=Get-DnsClientServerAddress -InterfaceIndex $item.InterfaceIndex "
        "-AddressFamily IPv4 -ErrorAction SilentlyContinue; "
        "[pscustomobject]@{InterfaceAlias=$item.InterfaceAlias; "
        "InterfaceIndex=$item.InterfaceIndex; "
        "IPv4=@($item.IPv4Address | ForEach-Object {$_.IPAddress}); "
        "Gateway=@($item.IPv4DefaultGateway | ForEach-Object {$_.NextHop}); "
        "Dns=@($dns.ServerAddresses)} "
        "}) | ConvertTo-Json -Compress -Depth 4"
    )
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
    try:
        proc = runner(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Odczyt adapterów jest niedostępny: {error}") from error
    if proc.returncode:
        raise RuntimeError("Nie udało się odczytać konfiguracji adapterów.")
    try:
        raw = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as error:
        raise RuntimeError("System zwrócił nieprawidłowe dane adapterów.") from error
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raise RuntimeError("Nieprawidłowy format konfiguracji adapterów.")

    def clean_addresses(value):
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            try:
                address = str(ipaddress.IPv4Address(item))
            except (ipaddress.AddressValueError, TypeError):
                continue
            if address not in result:
                result.append(address)
        return result

    adapters = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            index = int(row["InterfaceIndex"])
        except (KeyError, ValueError, TypeError):
            continue
        adapters.append({
            "name": str(row.get("InterfaceAlias") or "Niedostępne"),
            "index": index,
            "ipv4": clean_addresses(row.get("IPv4")),
            "gateway": clean_addresses(row.get("Gateway")),
            "dns": clean_addresses(row.get("Dns")),
        })
    return sorted(adapters, key=lambda item: item["index"])
