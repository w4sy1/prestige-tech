"""Offline porównanie zapisanych wyników inspekcji aplikacji ADB."""

import json
from pathlib import Path


def load_apps_snapshot(path):
    source = Path(path)
    if source.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Migawka Android przekracza limit 16 MiB.")
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    if (not isinstance(data, dict) or not isinstance(data.get("serial"), str)
            or not isinstance(data.get("apps"), list) or len(data["apps"]) > 2000
            or any(not isinstance(row, dict) or not isinstance(row.get("package"), str)
                   for row in data["apps"])):
        raise ValueError("Nieprawidłowy wynik inspekcji aplikacji.")
    return data


def compare_apps_snapshots(before, after):
    if before["serial"] != after["serial"]:
        raise ValueError("Migawki dotyczą różnych numerów serial urządzenia.")
    old = {row["package"]: row for row in before["apps"]}
    new = {row["package"]: row for row in after["apps"]}
    changes = []
    for package in sorted(old.keys() & new.keys()):
        left, right = old[package], new[package]
        fields = {}
        for field in ("version", "requested_permissions", "granted_permissions",
                      "active_special_access", "appops"):
            if left.get(field) != right.get(field):
                fields[field] = {"before": left.get(field), "after": right.get(field)}
        if fields:
            changes.append({"package": package, "fields": fields})
    return {"serial": before["serial"],
            "status": "COMPLETE" if before.get("status") == after.get("status") == "COMPLETE"
            else "UNKNOWN", "added": sorted(new.keys() - old.keys()),
            "removed": sorted(old.keys() - new.keys()), "changed": changes,
            "note": "Brak aplikacji w niepełnej migawce nie dowodzi odinstalowania."}
