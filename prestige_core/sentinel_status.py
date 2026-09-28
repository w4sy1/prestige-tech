"""Odczyt statusu Network Sentinel v2 z istniejącego mostu JSON."""

from datetime import datetime, timezone
from collections import deque
import json
from pathlib import Path


def read_sentinel_status(path, *, now=None):
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("module") != "network-sentinel" or data.get("bridgeVersion") != 2:
        raise ValueError("To nie jest status Network Sentinel bridge v2.")
    required = ("running", "admin", "deepCapture")
    if any(type(data.get(key)) is not bool for key in required):
        raise ValueError("Status Sentinel ma nieprawidłowe pola logiczne.")
    counts = ("onlineDevices", "newDevices", "threats", "alertCount")
    if any(type(data.get(key)) is not int or data[key] < 0 for key in counts):
        raise ValueError("Status Sentinel ma nieprawidłowe liczniki.")
    try:
        stamp = datetime.fromisoformat(data["timestamp"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Brak poprawnego czasu statusu Sentinel.") from error
    if stamp.tzinfo is None:
        raise ValueError("Czas statusu Sentinel nie zawiera strefy czasowej.")
    current = now or datetime.now(timezone.utc)
    age_seconds = (current - stamp).total_seconds()
    return {
        "module": data["module"], "version": str(data.get("version", "")),
        "running_reported": data["running"], "admin": data["admin"],
        "deep_capture": data["deepCapture"],
        "online_devices": data["onlineDevices"], "new_devices": data["newDevices"],
        "threats": data["threats"], "alert_count": data["alertCount"],
        "interface": str(data.get("interface") or ""),
        "ip": str(data.get("ip") or ""), "gateway": str(data.get("gateway") or ""),
        "timestamp": stamp.isoformat(), "age_seconds": age_seconds,
        "stale": age_seconds > 30 or age_seconds < -30,
        "source": str(source.resolve()),
    }


def read_sentinel_events(path, *, limit=200):
    """Odczytaj ostatnie alerty starego Network Sentinel bez zmiany logu."""
    if not 1 <= limit <= 1000:
        raise ValueError("Limit alertów musi mieścić się w zakresie 1–1000.")
    source = Path(path)
    with source.open("r", encoding="utf-8-sig") as stream:
        tail = deque(stream, maxlen=limit)
    events = []
    malformed = 0
    for line in tail:
        try:
            row = json.loads(line)
            if (not isinstance(row, dict) or not isinstance(row.get("Time"), str)
                    or not isinstance(row.get("Severity"), str)
                    or not isinstance(row.get("Type"), str)):
                raise ValueError("Nieprawidłowy alert.")
            events.append({"time": row["Time"], "severity": row["Severity"],
                           "type": row["Type"], "source_ip": str(row.get("SourceIP") or ""),
                           "category": str(row.get("Category") or "")})
        except (json.JSONDecodeError, ValueError):
            malformed += 1
    return {"status": "UNKNOWN" if malformed else "COMPLETE", "events": events,
            "malformed": malformed, "source": str(source.resolve())}
