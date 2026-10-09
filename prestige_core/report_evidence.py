"""Odczytowe źródła JSON dla Repair Report, bez automatycznej diagnozy."""

import hashlib
import json
from pathlib import Path
import re

from .event_history import validate_history
from .security_rules import CHECK_NAMES
from .system_snapshot import validate_snapshot


MAX_SOURCE_BYTES = 16 * 1024 * 1024


def source_sha256(path):
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ValueError("Wybierz zwykły plik źródłowy, bez dowiązania symbolicznego.")
    size = source.stat().st_size
    if size > MAX_SOURCE_BYTES:
        raise ValueError("Źródło raportu przekracza limit 16 MiB.")
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if source.stat().st_size != size:
        raise ValueError("Źródło zmieniło się podczas odczytu.")
    return digest.hexdigest()


def _describe(data):
    if not isinstance(data, dict):
        raise ValueError("Nieobsługiwany wynik JSON Centrum.")
    if data.get("mode") == "LOCAL MODE" and data.get("data_leaves_device") is False:
        if not isinstance(data.get("alerts"), list):
            raise ValueError("Nieprawidłowy wynik AI Center.")
        return "AI Center", (f"Lokalny wynik reguł: {len(data['alerts'])} alertów; "
                              "wymagana ocena technika.")
    if data.get("mode") == "EXTERNAL AI" and data.get("data_leaves_device") is True:
        if not isinstance(data.get("analysis"), str) or not isinstance(data.get("sent_metrics"), dict):
            raise ValueError("Nieprawidłowy wynik zewnętrznego AI.")
        return "AI Center", "Zapisana odpowiedź zewnętrznego AI; treść wymaga oceny technika."
    if (isinstance(data.get("coverage"), dict)
            and type(data.get("risk_score")) is int
            and type(data.get("unknown_checks")) is int
            and isinstance(data.get("alerts"), list)):
        if (not 0 <= data["risk_score"] <= 100 or data["unknown_checks"] < 0
                or set(data["coverage"]) != set(CHECK_NAMES)
                or any(value not in ("UNKNOWN", "EVALUATED")
                       for value in data["coverage"].values())
                or data["unknown_checks"] != sum(value == "UNKNOWN" for value in data["coverage"].values())):
            raise ValueError("Nieprawidłowy wynik Security Center.")
        return "Security Center", (f"Audyt konfiguracji: {data['unknown_checks']} kontroli UNKNOWN; "
                                    "wynik nie jest diagnozą infekcji.")
    if (data.get("status") in ("READY", "UNAVAILABLE")
            and type(data.get("termux_detected")) is bool
            and isinstance(data.get("commands"), dict)):
        if any(type(value) is not bool for value in data["commands"].values()):
            raise ValueError("Nieprawidłowy stan Termux Center.")
        return "Termux Center", "Odczyt stanu środowiska Termux; dostępność poleceń nie dowodzi ich działania."
    if data.get("schema_version") != 1:
        raise ValueError("Nieobsługiwany wynik JSON Centrum.")
    if (isinstance(data.get("files"), list) and type(data.get("complete")) is bool
            and isinstance(data.get("errors"), list)):
        if any(not isinstance(row, dict) or not isinstance(row.get("path"), str)
               or not isinstance(row.get("sha256"), str)
               or re.fullmatch(r"[a-fA-F0-9]{64}", row["sha256"]) is None
               for row in data["files"]):
            raise ValueError("Nieprawidłowy manifest Storage & Recovery.")
        return "Storage & Recovery", (f"Manifest kopii: {len(data['files'])} wpisów; "
                                      f"stan {'COMPLETE' if data['complete'] else 'INCOMPLETE'}.")
    if (isinstance(data.get("neighbors"), list)
            and isinstance(data.get("adapters"), list)
            and isinstance(data.get("source"), str)):
        rows = data["neighbors"]
        if any(not isinstance(row, dict) or not isinstance(row.get("ips"), list)
               for row in rows):
            raise ValueError("Nieprawidłowa migawka Network Center.")
        return "Network Center", f"Migawka sieci: {len(rows)} wpisów urządzeń; obserwacja może być niepełna."
    if "events" in data:
        history = validate_history(data)
        return "Monitor Center", f"Historia Monitora: {len(history['events'])} zapisanych zdarzeń; brak wpisu nie dowodzi braku zmiany."
    if "sections" in data:
        snapshot = validate_snapshot(data)
        unknown = sum(row["status"] == "UNKNOWN" for row in snapshot["sections"].values())
        return "System Center", f"Migawka systemu: {len(snapshot['sections'])} sekcji, {unknown} UNKNOWN."
    if "apps" in data:
        if (not isinstance(data.get("serial"), str) or not isinstance(data["apps"], list)
                or len(data["apps"]) > 2000
                or any(not isinstance(row, dict) or not isinstance(row.get("package"), str)
                       for row in data["apps"])):
            raise ValueError("Nieprawidłowa migawka Android Center.")
        return "Android Center", f"Migawka aplikacji: {len(data['apps'])} wpisów; kompletność wymaga oceny."
    if (data.get("hive") == "HKCU" and isinstance(data.get("operation"), str)
            and all(name in data for name in ("before", "applied", "current"))
            and data.get("status") in ("PLAN", "REFUSED")):
        return "Registry Manager", "Różnica wartości HKCU przed i po zmianie; stan bieżący jest chwilowy."
    raise ValueError("Nieobsługiwany format wyniku Centrum.")


def import_center_json(path):
    """Zwróć typ, neutralny opis i hash źródła; nie kopiuj danych prywatnych."""
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ValueError("Wybierz zwykły plik źródłowy, bez dowiązania symbolicznego.")
    with source.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("Źródło raportu przekracza limit 16 MiB.")
    digest = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw.decode("utf-8-sig"))
    center, summary = _describe(data)
    if source_sha256(source) != digest:
        raise ValueError("Źródło zmieniło się podczas importu.")
    return {"center": center, "summary": summary, "sha256": digest,
            "path": str(source.resolve())}
