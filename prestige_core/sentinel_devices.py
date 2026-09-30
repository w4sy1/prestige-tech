"""Bezpieczny odczyt list znanych i zaufanych urządzeń starego Sentinel."""

import json
import ipaddress
from pathlib import Path
import re


_MAC = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\Z")


def _mac(value):
    normalized = str(value or "").lower().replace("-", ":")
    return normalized if _MAC.fullmatch(normalized) else ""


def read_device_registry(path):
    source = Path(path)
    rows = json.loads(source.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise ValueError("Lista urządzeń Sentinel musi być tablicą JSON.")
    devices = []
    invalid = 0
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("Key"), str) or not row["Key"].strip():
            invalid += 1
            continue
        devices.append({key.lower(): str(row.get(key) or "")
                        for key in ("Key", "IP", "MAC", "Name", "Added")})
    return {"status": "UNKNOWN" if invalid else "COMPLETE", "devices": devices,
            "invalid_rows": invalid, "source": str(source.resolve())}


def correlate_devices(known, trusted):
    """Wyróżnij niespójności list bez domniemywania, że host jest online."""
    known_by_key = {row["key"]: row for row in known["devices"]}
    trusted_by_key = {row["key"]: row for row in trusted["devices"]}
    rows = []
    for key in sorted(known_by_key.keys() | trusted_by_key.keys()):
        base = known_by_key.get(key) or trusted_by_key[key]
        rows.append({"key": key, "ip": base["ip"], "mac": base["mac"],
                     "name": base["name"], "known": key in known_by_key,
                     "trusted": key in trusted_by_key,
                     "trusted_ip": trusted_by_key[key]["ip"] if key in trusted_by_key else "",
                     "ip_mismatch": (key in known_by_key and key in trusted_by_key
                                     and known_by_key[key]["ip"] != trusted_by_key[key]["ip"])})
    return {"status": "UNKNOWN" if "UNKNOWN" in (known["status"], trusted["status"])
            else "COMPLETE", "devices": rows}


def assess_observations(registry, discovery):
    """Porównaj jawny skan z listami bez wnioskowania offline i bez blokad."""
    if (not isinstance(registry, dict) or registry.get("status") != "COMPLETE"
            or not isinstance(registry.get("devices"), list)
            or not isinstance(discovery, dict)
            or not isinstance(discovery.get("observed"), list)):
        raise ValueError("Wymagany kompletny rejestr i wynik skanu.")
    registered_by_mac = {_mac(row.get("mac") or row.get("key")): row
                         for row in registry["devices"] if _mac(row.get("mac") or row.get("key"))}
    registered_by_ip = {row["ip"]: row for row in registry["devices"] if row.get("ip")}
    findings = []
    for row in discovery["observed"][:256]:
        if not isinstance(row, dict) or row.get("evidence") not in ("ICMP", "Nmap"):
            continue
        try:
            ip = str(ipaddress.IPv4Address(row["ip"]))
        except (KeyError, ValueError, TypeError):
            continue
        mac = _mac(row.get("mac"))
        same_mac = registered_by_mac.get(mac) if mac else None
        same_ip = registered_by_ip.get(ip)
        if same_ip and mac and _mac(same_ip.get("mac") or same_ip.get("key")) not in ("", mac):
            kind = "POSSIBLE_MAC_CHANGE"
        elif same_mac and same_mac.get("ip") and same_mac["ip"] != ip:
            kind = "IP_CHANGE"
        elif not same_mac and not same_ip:
            kind = "NEW_DEVICE"
        else:
            continue
        findings.append({"type": kind, "ip": ip, "mac": mac,
                         "evidence": row["evidence"],
                         "note": "Obserwacja wymaga potwierdzenia; DHCP i cache mogą zmieniać adresy."})
    return {"status": "UNKNOWN" if discovery.get("status") != "COMPLETE" else "COMPLETE",
            "findings": findings,
            "note": "Brak obserwacji nie dowodzi offline. Wyniki nie uruchamiają blokady."}
