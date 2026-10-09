"""Neutralne podsumowania bieżących wyników do formularza serwisowego."""


def summarize_live_result(center, result):
    if not isinstance(result, dict):
        raise ValueError("Brak bieżącego wyniku Centrum.")
    if center == "Android":
        apps = result.get("apps")
        if not isinstance(apps, list) or any(not isinstance(row, dict) for row in apps):
            raise ValueError("Brak poprawnej listy aplikacji Android.")
        status = result.get("status", "UNKNOWN")
        if status not in ("COMPLETE", "PARTIAL", "UNKNOWN"):
            raise ValueError("Nieznany stan odczytu Android.")
        note = f"Android Center: odczytano {len(apps)} wpisów aplikacji; status {status}. "
        if result.get("truncated"):
            note += "Osiągnięto limit listy. "
        note += "Lista i deklaracje uprawnień nie są diagnozą bezpieczeństwa."
    elif center == "Network":
        if (result.get("status") not in ("COMPLETE", "UNKNOWN")
                or type(result.get("probed")) is not int or result["probed"] < 0
                or not isinstance(result.get("responsive"), list)
                or not isinstance(result.get("observed"), list)):
            raise ValueError("Brak poprawnego wyniku lokalnego skanu sieci.")
        cache = sum(isinstance(row, dict) and row.get("evidence") == "Cache — dostępność nieznana"
                    for row in result["observed"])
        note = (f"Network Center: jawny skan lokalny; status {result['status']}, "
                f"sondowano {result['probed']} adresów, odpowiedzi ICMP: "
                f"{len(result['responsive'])}, wpisy cache bez potwierdzenia: {cache}. "
                "Brak odpowiedzi nie dowodzi wyłączenia hosta.")
    elif center == "Monitor":
        from .event_history import validate_history
        history = validate_history(result)
        note = (f"Monitor Center: {len(history['events'])} zapisanych zdarzeń. "
                "Brak wpisu nie dowodzi braku zmian; zakres i kompletność wymagają oceny.")
    elif center == "Registry":
        if (result.get("status") not in ("COMPLETE", "UNKNOWN", "CANCELLED")
                or type(result.get("total")) is not int or type(result.get("processed")) is not int
                or not 0 <= result["processed"] <= result["total"]
                or not isinstance(result.get("counts"), dict)):
            raise ValueError("Brak poprawnego podsumowania audytu Registry.")
        note = (f"Registry Manager: odczyt {result['processed']}/{result['total']} operacji; "
                f"status {result['status']}, błędy {result['counts'].get('ERROR', 0)}. "
                "Nieustawiona zasada nie oznacza potwierdzonej wartości konfiguracji.")
    elif center == "Storage":
        if (type(result.get("copied")) is not int or result["copied"] < 0
                or type(result.get("ok")) is not bool
                or not isinstance(result.get("errors"), list)):
            raise ValueError("Brak poprawnego podsumowania kopii Storage.")
        note = (f"Storage & Recovery: skopiowano {result['copied']} plików; "
                f"status {'COMPLETE' if result['ok'] else 'INCOMPLETE'}, "
                f"błędy {len(result['errors'])}.")
        if result.get("vss_cleanup_required"):
            note += " Dziennik VSS wymaga sprawdzenia i oczyszczenia."
        note += " Weryfikację kopii i odtworzenia zapisz osobno."
    elif center == "Termux":
        if (result.get("status") not in ("READY", "UNAVAILABLE")
                or type(result.get("termux_detected")) is not bool
                or not isinstance(result.get("commands"), dict)):
            raise ValueError("Brak poprawnego odczytu środowiska Termux.")
        note = (f"Termux Center: odczyt stanu środowiska {result['status']}; "
                "dostępność poleceń nie potwierdza ich działania.")
    elif center == "AI":
        mode = result.get("mode")
        if mode == "LOCAL MODE" and result.get("data_leaves_device") is False:
            alerts = result.get("alerts")
            if not isinstance(alerts, list):
                raise ValueError("Brak poprawnego wyniku lokalnego AI.")
            note = f"AI Center: lokalna analiza regułowa, {len(alerts)} alertów; wynik wymaga oceny technika."
        elif mode == "EXTERNAL AI" and result.get("data_leaves_device") is True:
            if not isinstance(result.get("analysis"), str):
                raise ValueError("Brak poprawnej odpowiedzi zewnętrznego AI.")
            note = "AI Center: otrzymano odpowiedź zewnętrznego modelu; wynik wymaga oceny technika."
        else:
            raise ValueError("Nieobsługiwany wynik AI Center.")
    else:
        raise ValueError("Nieobsługiwane Centrum.")
    return {"wykonane_czynnosci": note}
