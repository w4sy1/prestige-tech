"""Proste plany pomocy dla użytkownika, bez wykonywania zmian w systemie."""

from dataclasses import dataclass
from pathlib import Path
import shutil


@dataclass(frozen=True)
class HelpStep:
    title: str
    center: str
    operation: str
    automatic: bool = False


_PROBLEMS = {
    "slow_internet": (
        "Internet działa wolno",
        "Najpierw sprawdzimy połączenie. Zmiany ustawień wymagają osobnego potwierdzenia.",
        (
            HelpStep("Sprawdź połączenie i router", "Network Center", "internet-diagnostic"),
            HelpStep("Sprawdź ustawienia połączenia", "Network Center", "internet-context"),
            HelpStep("Pokaż plan odświeżenia pamięci adresów", "Network Center", "flush-dns"),
        ),
    ),
    "no_sound": (
        "Nie słychać dźwięku",
        "Sprawdzimy wyciszenie i wybrane urządzenie. Niczego nie przełączymy bez potwierdzenia.",
        (
            HelpStep("Sprawdź głośność i wyciszenie", "System Center", "audio-volume-check"),
            HelpStep("Sprawdź wyjście dźwięku", "System Center", "audio-output-check"),
        ),
    ),
    "low_disk_space": (
        "Brakuje miejsca na dysku",
        "Pokażemy pliki tymczasowe przed czyszczeniem. Dokumenty i Pobrane pozostają nietknięte.",
        (
            HelpStep("Sprawdź wolne miejsce", "System Center", "disk-space-check"),
            HelpStep("Pokaż plan czyszczenia plików tymczasowych", "System Center", "temp-cleanup-plan"),
        ),
    ),
    "printer_unavailable": (
        "Drukarka nie odpowiada",
        "Sprawdzimy stan usługi drukowania. Restart usługi wymaga osobnego potwierdzenia.",
        (
            HelpStep("Sprawdź usługę drukowania", "System Center", "spooler-status"),
        ),
    ),
}


def available_problems():
    return tuple({"id": key, "title": item[0]} for key, item in _PROBLEMS.items())


def help_plan(problem_id):
    if problem_id not in _PROBLEMS:
        raise ValueError("Nieznany problem.")
    title, introduction, steps = _PROBLEMS[problem_id]
    return {"problem_id": problem_id, "title": title, "introduction": introduction,
            "steps": [step.__dict__.copy() for step in steps],
            "status": "PLAN", "system_changed": False,
            "note": "To plan pomocy. Każdy wynik trzeba sprawdzić przed ogłoszeniem naprawy."}


def traffic_light(*, threat_confirmed=False, attention_needed=False, checks_complete=False):
    """Brak danych nie daje zielonego statusu."""
    if threat_confirmed:
        return {"color": "red", "label": "Wykryto problem wymagający uwagi"}
    if attention_needed or not checks_complete:
        return {"color": "yellow", "label": "Warto sprawdzić"}
    return {"color": "green", "label": "Sprawdzone elementy działają poprawnie"}


def check_disk_space(path=None, *, disk_usage=shutil.disk_usage):
    """Rzeczywisty, odczytowy pomiar miejsca; brak diagnozy zbędnych plików."""
    location = Path(path or Path.home()).resolve(strict=True)
    usage = disk_usage(location)
    if usage.total <= 0:
        raise ValueError("Nie udało się odczytać pojemności dysku.")
    percent_free = round(100 * usage.free / usage.total, 1)
    return {"status": "COMPLETE", "path": str(location), "total_bytes": usage.total,
            "free_bytes": usage.free, "free_percent": percent_free,
            "indicator": traffic_light(attention_needed=percent_free < 15,
                                       checks_complete=True),
            "system_changed": False}


def check_internet(*, target="1.1.1.1", gateway=None, diagnose=None):
    """Wykorzystuje istniejącą diagnostykę Network Center; nie naprawia sieci."""
    if diagnose is None:
        from .internet_diagnostic import diagnose as diagnose
    result = diagnose(target, gateway=gateway, count=3, test_http=True)
    if result.get("status") != "COMPLETE":
        return {"status": "INCOMPLETE", "reason": result.get("reason", "Brak wyniku."),
                "indicator": traffic_light(), "system_changed": False}
    internet = result["internet"]
    dns = result["dns"]
    web = result.get("web", {})
    web_response = any(item.get("status") == "RESPONSE" for item in web.values())
    checks_complete = bool(web)
    working = internet["received"] > 0 and dns["ok"] and web_response
    return {"status": "COMPLETE", "target": result["target"],
            "received": internet["received"], "samples": internet["samples"],
            "dns_ok": dns["ok"], "web_response": web_response,
            "classification": result["classification"],
            "indicator": traffic_light(attention_needed=not working,
                                       checks_complete=checks_complete),
            "system_changed": False,
            "note": "Sam ping może być blokowany; wynik trzeba zestawić z testem strony."}
