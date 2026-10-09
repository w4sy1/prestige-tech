"""Prosty lokalny raport do samodzielnego udostępnienia bliskiej osobie."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


def build_family_summary(directory, *, now=None):
    folder = Path(directory)
    if not folder.is_dir():
        raise ValueError("Wybierz katalog zapisanych przeglądów.")
    current = now or datetime.now(timezone.utc)
    cutoff = current.astimezone(timezone.utc) - timedelta(days=7)
    records = []
    unreadable = 0
    for path in sorted(folder.glob("prestige-check-*.json"), reverse=True)[:100]:
        try:
            if path.stat().st_size > 128 * 1024:
                raise ValueError("Zbyt duży plik")
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            stamp = datetime.fromisoformat(data["created_utc"])
            if (data.get("schema_version") != 1 or stamp.tzinfo is None
                    or not isinstance(data.get("checks"), dict)):
                raise ValueError("Nieprawidłowy raport")
            if cutoff <= stamp.astimezone(timezone.utc) <= current.astimezone(timezone.utc):
                records.append((stamp, data["checks"]))
        except (OSError, ValueError, KeyError, TypeError, UnicodeError):
            unreadable += 1
    records.sort(key=lambda item: item[0], reverse=True)
    if not records:
        raise ValueError("Brak poprawnych przeglądów z ostatnich 7 dni.")
    latest = {}
    for stamp, checks in records:
        for name, row in checks.items():
            if name not in ("disk", "printer", "audio", "internet") or name in latest or not isinstance(row, dict):
                continue
            entry = {"checked_utc": stamp.astimezone(timezone.utc).isoformat(),
                     "status": row.get("status", "UNKNOWN")}
            if name == "disk" and isinstance(row.get("free_percent"), (int, float)):
                entry["free_percent"] = row["free_percent"]
            elif name == "printer":
                entry["service"] = row.get("service", "UNKNOWN")
                entry["printer_count"] = row.get("printer_count")
            elif name == "audio":
                entry["device_count"] = row.get("device_count")
            elif name == "internet":
                entry["dns_ok"] = row.get("dns_ok")
                entry["web_response"] = row.get("web_response")
            latest[name] = entry
    missing = sorted(set(("disk", "printer", "audio", "internet")) - set(latest))
    return {"schema_version": 1, "period_days": 7, "reports_read": len(records),
            "unreadable_reports": unreadable, "latest_checks": latest,
            "not_checked": missing, "sent": False,
            "note": "Raport obejmuje tylko wykonane odczyty. Nie potwierdza braku wirusów ani aktualności systemu."}


def render_family_text(summary):
    names = {"disk": "Miejsce na dysku", "printer": "Drukarka",
             "audio": "Dźwięk", "internet": "Internet"}
    lines = ["PRESTIGE TECH — stan sprawdzonych elementów", "Ostatnie 7 dni", ""]
    for key, title in names.items():
        row = summary["latest_checks"].get(key)
        if not row:
            lines.append(f"{title}: nie sprawdzono")
        elif key == "disk" and "free_percent" in row:
            lines.append(f"{title}: {row['free_percent']}% wolnego miejsca ({row['checked_utc']})")
        elif key == "printer":
            description = ("usługa drukowania działa; wydruku nie testowano"
                           if row.get("status") == "COMPLETE" and row.get("service") == "Running" else
                           "stanu drukowania nie potwierdzono")
            lines.append(f"{title}: {description} ({row['checked_utc']})")
        elif key == "audio":
            description = (f"wykryto {row.get('device_count', 0)} urządzeń; "
                           "wyciszenia i odtwarzania nie testowano"
                           if row.get("status") == "PARTIAL" else "odczyt urządzeń niedostępny")
            lines.append(f"{title}: {description} ({row['checked_utc']})")
        else:
            description = ("strona odpowiedziała i nazwa została rozpoznana"
                           if row.get("status") == "COMPLETE" and row.get("dns_ok") is True
                           and row.get("web_response") is True else
                           "wynik nie potwierdza działającego połączenia")
            lines.append(f"{title}: {description} ({row['checked_utc']})")
    lines.extend(("", summary["note"], "Raport zapisano lokalnie; niczego nie wysłano."))
    return "\n".join(lines) + "\n"


def save_family_text(summary, destination):
    path = Path(destination)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(render_family_text(summary))
    return path
