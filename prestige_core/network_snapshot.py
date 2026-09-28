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


def make_snapshot(*, neighbors, adapters, captured_at=None):
    if not isinstance(neighbors, list) or not isinstance(adapters, list):
        raise ValueError("Migawka wymaga odczytu urządzeń i adapterów.")
    return {
        "schema_version": 1,
        "captured_at_utc": captured_at or datetime.now(timezone.utc).isoformat(),
        "source": "lokalny cache systemu i konfiguracja adapterów",
        "observation_complete": False,
        "neighbors": neighbors,
        "adapters": adapters,
    }


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
