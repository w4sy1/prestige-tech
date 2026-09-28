"""Odczyt istniejącej historii urządzeń Network Sentinel bez jej modyfikacji."""

from collections import deque
import json
from pathlib import Path


def read_device_history(path, *, limit=300):
    if not 1 <= limit <= 1000:
        raise ValueError("Limit historii musi być w zakresie 1–1000.")
    rows = deque(maxlen=limit)
    invalid = 0
    with Path(path).open("r", encoding="utf-8-sig", errors="replace") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue
            if not isinstance(row, dict) or not isinstance(row.get("Event"), str):
                invalid += 1
                continue
            rows.append({name: str(row.get(name) or "") for name in ("Time", "Key", "IP", "Event", "Details")})
    return {"status": "UNKNOWN" if invalid else "COMPLETE", "invalid_rows": invalid,
            "events": list(reversed(rows)), "source": str(Path(path).resolve())}
