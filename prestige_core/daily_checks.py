"""Jednorazowy, odczytowy przegląd komputera do wywołania z harmonogramu."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

from .senior_assistant import check_disk_space, check_internet, traffic_light
from .system_help_checks import read_audio_devices, read_printer_state


ALLOWED = ("disk", "printer", "audio", "internet")


def default_report_dir():
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "PrestigeTech" / "DailyChecks"


def run_daily_checks(enabled=("disk",), *, probes=None, now=None):
    if not enabled or any(name not in ALLOWED for name in enabled) or len(set(enabled)) != len(enabled):
        raise ValueError("Wybierz unikalne, znane testy.")
    probes = probes or {"disk": check_disk_space, "printer": read_printer_state,
                        "audio": read_audio_devices, "internet": check_internet}
    rows = {}
    attention = False
    complete = True
    for name in enabled:
        try:
            result = probes[name]()
            if name == "disk":
                row = {"status": result["status"], "free_percent": result["free_percent"]}
                needs_attention = result["indicator"]["color"] != "green"
            elif name == "printer":
                row = {"status": result["status"], "service": result["service"],
                       "printer_count": len(result["printers"])}
                needs_attention = result["status"] != "COMPLETE" or result["service"] != "Running"
            elif name == "audio":
                row = {"status": "PARTIAL" if result["status"] == "COMPLETE" else "UNKNOWN",
                       "device_count": len(result["devices"]), "mute": "UNKNOWN"}
                needs_attention = True
            else:
                row = {"status": result["status"], "dns_ok": result.get("dns_ok"),
                       "web_response": result.get("web_response")}
                needs_attention = result["indicator"]["color"] != "green"
            rows[name] = row
            attention |= needs_attention
            complete &= row["status"] == "COMPLETE"
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
            rows[name] = {"status": "UNKNOWN", "error_type": type(error).__name__}
            attention = True
            complete = False
    stamp = now or datetime.now(timezone.utc)
    return {"schema_version": 1, "created_utc": stamp.astimezone(timezone.utc).isoformat(),
            "checks": rows, "indicator": traffic_light(attention_needed=attention,
                                                        checks_complete=complete),
            "system_changed": False,
            "note": "Wynik dotyczy tylko wykonanych testów. Nie wykonano napraw."}


def save_daily_report(report, directory):
    folder = Path(directory).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / ("prestige-check-" + uuid.uuid4().hex + ".json")
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description="Odczytowy przegląd Prestige Tech bez napraw")
    parser.add_argument("--out", type=Path, required=True, help="Katalog nowych raportów JSON")
    parser.add_argument("--printer", action="store_true", help="Odczytaj drukarkę")
    parser.add_argument("--audio", action="store_true", help="Odczytaj urządzenia dźwięku")
    parser.add_argument("--internet", action="store_true", help="Wykonaj sondy do zewnętrznych hostów")
    args = parser.parse_args(argv)
    enabled = ("disk",) + tuple(name for name in ("printer", "audio", "internet")
                                if getattr(args, name))
    report = run_daily_checks(enabled)
    print(save_daily_report(report, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
