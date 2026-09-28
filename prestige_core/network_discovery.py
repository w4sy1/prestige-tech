"""Ograniczony skan ICMP bieżącej lokalnej podsieci IPv4 w Windows."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .network import read_neighbors


def load_oui(path):
    """Odczytaj lokalną bazę OUI; nie pobieraj danych z sieci."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Baza OUI musi być obiektem JSON.")
    result = {}
    for key, value in data.items():
        prefix = str(key).replace(":", "").replace("-", "").upper()
        if not re.fullmatch(r"[0-9A-F]{6}", prefix) or not isinstance(value, str):
            raise ValueError("Nieprawidłowy wpis w bazie OUI.")
        result[prefix] = value[:200]
    return result


def vendor_for_mac(mac, oui):
    if not mac:
        return ""
    normalized = mac.replace(":", "").replace("-", "").upper()
    if not re.fullmatch(r"[0-9A-F]{12}", normalized):
        return ""
    if int(normalized[:2], 16) & 2:
        return "Adres lokalny/losowy — producent nieznany"
    return oui.get(normalized[:6], "")


def reverse_name(address, *, runner=subprocess.run):
    """Osobny proces ogranicza czas blokującego zapytania gethostbyaddr."""
    ip = str(ipaddress.IPv4Address(address))
    code = "import socket,sys; print(socket.gethostbyaddr(sys.argv[1])[0])"
    try:
        result = runner([sys.executable, "-c", code, ip], capture_output=True,
                        text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()[:253] if result.returncode == 0 else ""


def local_scopes(*, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Wykrywanie lokalnych podsieci wymaga Windows.")
    script = ("@(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | "
              "Where-Object {$_.AddressState -eq 'Preferred' -and $_.PrefixOrigin -ne 'WellKnown'} | "
              "Select-Object IPAddress,PrefixLength,InterfaceAlias,InterfaceIndex) | ConvertTo-Json -Compress")
    try:
        result = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                        capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Nie odczytano lokalnych podsieci.") from error
    if result.returncode:
        raise RuntimeError("Nie odczytano lokalnych podsieci.")
    try:
        rows = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as error:
        raise RuntimeError("Nieprawidłowy odczyt lokalnych podsieci.") from error
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        raise RuntimeError("Nieprawidłowy format podsieci.")
    scopes = []
    for row in rows:
        try:
            address = ipaddress.IPv4Address(row["IPAddress"])
            prefix = int(row["PrefixLength"])
            network = ipaddress.IPv4Network((address, prefix), strict=False)
            if not address.is_private or address.is_loopback or address.is_link_local:
                continue
            if prefix < 24:
                network = ipaddress.IPv4Network((address, 24), strict=False)
            scopes.append({"ip": str(address), "scope": str(network),
                           "interface": str(row.get("InterfaceAlias") or ""),
                           "index": int(row.get("InterfaceIndex") or 0),
                           "capped": prefix < 24})
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(scopes, key=lambda row: (row["index"], row["ip"]))


def plan_targets(scope, local_ip):
    network = ipaddress.IPv4Network(scope, strict=True)
    address = ipaddress.IPv4Address(local_ip)
    if address not in network or not address.is_private or network.prefixlen < 24:
        raise ValueError("Skan może obejmować tylko lokalną podsieć IPv4 o zakresie do /24.")
    return [str(target) for target in network.hosts() if target != address]


def scan_local_scope(scope, local_ip, *, cancel_event=None, ping_runner=subprocess.run,
                     neighbors_reader=read_neighbors, max_workers=16, oui=None,
                     resolve_names=False, name_resolver=reverse_name):
    targets = plan_targets(scope, local_ip)
    if not 1 <= max_workers <= 32:
        raise ValueError("Niedozwolona liczba równoległych sond.")
    responses = []
    errors = 0

    def probe(target):
        if cancel_event is not None and cancel_event.is_set():
            return target, None
        try:
            result = ping_runner(["ping", "-n", "1", "-w", "300", target],
                                 capture_output=True, text=True, timeout=2, check=False)
            return target, result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return target, None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(probe, target) for target in targets]
        for future in as_completed(futures):
            target, reachable = future.result()
            if reachable is True:
                responses.append(target)
            elif reachable is None:
                errors += 1
    try:
        neighbors = neighbors_reader()
    except RuntimeError:
        neighbors = []
        errors += 1
    by_ip = {ip: row["mac"] for row in neighbors for ip in row["ips"]}
    responsive = [{"ip": ip, "mac": by_ip.get(ip)}
                  for ip in sorted(responses, key=ipaddress.IPv4Address)]
    for row in responsive:
        row["vendor"] = vendor_for_mac(row["mac"], oui or {})
        row["hostname"] = ""
    if resolve_names and not (cancel_event is not None and cancel_event.is_set()):
        with ThreadPoolExecutor(max_workers=min(8, max_workers)) as pool:
            futures = {pool.submit(name_resolver, row["ip"]): row for row in responsive}
            for future in as_completed(futures):
                if cancel_event is not None and cancel_event.is_set():
                    break
                try:
                    futures[future]["hostname"] = future.result()
                except (OSError, ValueError, RuntimeError):
                    errors += 1
    return {"scope": scope, "local_ip": local_ip, "probed": len(targets),
            "cancelled": cancel_event is not None and cancel_event.is_set(),
            "status": "UNKNOWN" if errors or (cancel_event is not None and cancel_event.is_set()) else "COMPLETE",
            "probe_errors": errors,
            "responsive": responsive,
            "note": "Brak odpowiedzi ICMP nie dowodzi, że urządzenie jest offline."}
