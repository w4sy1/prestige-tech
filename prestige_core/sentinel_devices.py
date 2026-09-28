"""Bezpieczny odczyt list znanych i zaufanych urządzeń starego Sentinel."""

import json
from pathlib import Path


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
