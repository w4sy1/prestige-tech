"""Jawne, lokalne migawki odczytowego stanu sieci."""

from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import re


_MAC = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\Z")


def _mac_key(value):
    key = value.lower().replace("-", ":")
    return key if _MAC.fullmatch(key) else value.lower()


def _ips(values):
    return [str(address) for address in sorted(
        {ipaddress.ip_address(value) for value in values},
        key=lambda address: (address.version, int(address)))]


def make_snapshot(*, neighbors, adapters, discovery=None, captured_at=None):
    if not isinstance(neighbors, list) or not isinstance(adapters, list):
        raise ValueError("Migawka wymaga odczytu urządzeń i adapterów.")
    merged = [{**row, "ips": list(row.get("ips", []))} for row in neighbors]
    result = {
        "schema_version": 1,
        "captured_at_utc": captured_at or datetime.now(timezone.utc).isoformat(),
        "source": "lokalny cache systemu i konfiguracja adapterów",
        "observation_complete": False,
        "neighbors": merged,
        "adapters": adapters,
    }
    if discovery is not None:
        if not isinstance(discovery, dict) or not isinstance(discovery.get("observed"), list):
            raise ValueError("Nieprawidłowy wynik wykrywania.")
        by_mac = {_mac_key(row["mac"]): row for row in merged if row.get("mac")}
        without_mac = []
        for row in discovery["observed"]:
            if not isinstance(row, dict) or not isinstance(row.get("ip"), str):
                raise ValueError("Nieprawidłowa obserwacja urządzenia.")
            address = str(ipaddress.IPv4Address(row["ip"]))
            mac = row.get("mac")
            if not mac:
                if row.get("evidence") in ("ICMP", "Nmap"):
                    without_mac.append(address)
                continue
            if not isinstance(mac, str) or not _MAC.fullmatch(_mac_key(mac)):
                raise ValueError("Nieprawidłowy MAC w wyniku wykrywania.")
            key = _mac_key(mac)
            current = by_mac.get(key)
            if current is None:
                current = {"mac": key, "ips": []}
                merged.append(current)
                by_mac[key] = current
            if address not in current["ips"]:
                current["ips"].append(address)
            for field in ("hostname", "vendor"):
                if row.get(field):
                    current[field] = str(row[field])[:253]
        result["source"] += "; ostatni jawny skan lokalny"
        result["discovery"] = {
            "scope": str(discovery.get("scope") or ""),
            "status": str(discovery.get("status") or "UNKNOWN"),
            "probed": int(discovery.get("probed") or 0),
            "icmp_responsive": len(discovery.get("responsive") or []),
            "nmap_found": int(discovery.get("nmap_found") or 0),
            "responsive_without_mac": sorted(set(without_mac), key=ipaddress.IPv4Address),
        }
    return result


def save_snapshot(snapshot, destination):
    """Zapisz tylko nowy plik; nigdy nie nadpisuj wcześniejszej migawki."""
    path = Path(destination)
    content = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)
    return path


def compare_snapshots(earlier, later):
    def hosts(snapshot):
        if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
            raise ValueError("Nieobsługiwana migawka sieci.")
        if isinstance(snapshot.get("neighbors"), list):
            rows = snapshot["neighbors"]
        elif isinstance(snapshot.get("hosts"), dict):
            rows = list(snapshot["hosts"].values())
        else:
            raise ValueError("Nieobsługiwana migawka sieci.")
        if any(not isinstance(row, dict) or not isinstance(row.get("mac"), str)
               or not isinstance(row.get("ips"), list) for row in rows):
            raise ValueError("Nieprawidłowy wpis urządzenia w migawce.")
        result = {}
        for row in rows:
            mac = _mac_key(row["mac"])
            if mac not in result:
                result[mac] = {**row, "mac": mac, "ips": _ips(row["ips"])}
                continue
            current = result[mac]
            current["ips"] = _ips([*current["ips"], *row["ips"]])
            for field in ("hostname", "vendor", "status"):
                if row.get(field):
                    current[field] = row[field]
        return result

    before, after = hosts(earlier), hosts(later)
    return {
        "newly_observed": [after[mac] for mac in sorted(after.keys() - before.keys())],
        "not_observed_now": [before[mac] for mac in sorted(before.keys() - after.keys())],
        "changed_ips": [
            {"mac": mac, "before": before[mac].get("ips", []), "after": after[mac].get("ips", [])}
            for mac in sorted(before.keys() & after.keys())
            if before[mac].get("ips", []) != after[mac].get("ips", [])
        ],
        "changed_hostnames": [
            {"mac": mac, "before": before[mac].get("hostname", ""),
             "after": after[mac].get("hostname", "")}
            for mac in sorted(before.keys() & after.keys())
            if before[mac].get("hostname", "") != after[mac].get("hostname", "")
        ],
        "changed_vendors": [
            {"mac": mac, "before": before[mac].get("vendor", ""),
             "after": after[mac].get("vendor", "")}
            for mac in sorted(before.keys() & after.keys())
            if before[mac].get("vendor", "") != after[mac].get("vendor", "")
        ],
        "note": "Brak wpisu w cache nie potwierdza, że urządzenie jest offline.",
    }
