"""Mapa miejsc autostartu z istniejącego odczytu Malware Triage."""


AREAS = {
    "processes": "Uruchomione procesy",
    "startup": "Autostart użytkownika",
    "services": "Usługi systemowe",
    "tasks": "Zaplanowane zadania",
    "wmi": "Subskrypcje WMI",
    "registry": "Klucze rejestru",
    "drivers": "Sterowniki",
    "browser_extensions": "Rozszerzenia Chromium",
    "firefox_extensions": "Rozszerzenia Firefox",
    "profiles": "Profile PowerShell",
    "root_certificates": "Certyfikaty główne",
    "hosts": "Plik hosts",
    "proxy": "Proxy",
    "dns": "Ustawienia DNS",
    "connections": "Połączenia sieciowe",
}


def overview(triage):
    if not isinstance(triage, dict) or not isinstance(triage.get("evidence"), dict):
        raise ValueError("Wymagany wynik Malware Triage z dowodami.")
    evidence = triage["evidence"]
    areas = []
    for key, label in AREAS.items():
        section = evidence.get(key)
        status = section.get("status", "UNKNOWN") if isinstance(section, dict) else "UNKNOWN"
        rows = section.get("data", []) if isinstance(section, dict) else []
        count = len(rows) if isinstance(rows, list) else None
        areas.append({"id": key, "name": label, "status": status, "items": count})
    return {"areas": areas, "alerts": len(triage.get("alerts", [])),
            "correlations": len(triage.get("correlations", [])),
            "firmware": "UNKNOWN",
            "note": "Obecność wpisu nie oznacza infekcji. Odczyt BIOS/UEFI i Secure Boot nie potwierdza integralności firmware; wymaga zaufanego wzorca lub narzędzia producenta."}
