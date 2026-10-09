"""Odczytowa inwentaryzacja urządzeń USB PnP, bez testu zapisu nośnika."""

import json
import os
import re
import subprocess


_ID = re.compile(r"^USB\\VID_([0-9A-F]{4})&PID_([0-9A-F]{4})(?:[&\\]|$)", re.I)


def read_usb_devices(*, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Inwentaryzacja USB wymaga Windows.")
    script = ("@(Get-PnpDevice -PresentOnly -ErrorAction Stop | "
              "Where-Object { $_.InstanceId -match '^USB\\VID_[0-9A-Fa-f]{4}&PID_[0-9A-Fa-f]{4}' } | "
              "Select-Object InstanceId,FriendlyName,Class,Status) | "
              "ConvertTo-Json -Compress -Depth 3")
    try:
        result = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                        capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Nie odczytano urządzeń USB.") from error
    if result.returncode:
        raise RuntimeError("Odczyt PnP USB nie powiódł się.")
    try:
        raw = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as error:
        raise RuntimeError("Nieprawidłowy wynik PnP USB.") from error
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raise RuntimeError("Nieprawidłowa lista PnP USB.")
    rows = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("InstanceId") or "")
        match = _ID.match(identifier)
        if match:
            rows.append({"instance_id": identifier, "vid": match.group(1).upper(),
                         "pid": match.group(2).upper(),
                         "name": str(item.get("FriendlyName") or "Nieznane"),
                         "class": str(item.get("Class") or "Nieznana"),
                         "status": str(item.get("Status") or "UNKNOWN")})
    return {"devices": rows, "count": len(rows),
            "note": "Lista PnP obejmuje także koncentratory i inne urządzenia USB; nie jest testem pamięci."}
