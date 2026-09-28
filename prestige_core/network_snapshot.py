"""Jawne, lokalne migawki odczytowego stanu sieci."""

from datetime import datetime, timezone
import json
from pathlib import Path


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
        return {row["mac"].lower(): row for row in rows}

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
