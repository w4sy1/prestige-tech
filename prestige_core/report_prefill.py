"""Ostrożne wypełnianie formularza serwisowego wynikami Centrów."""


def summarize_center_result(center, action, result):
    """Zwróć wyłącznie zwięzłe fakty; dane klienta i test końcowy zostają puste."""
    if not isinstance(result, dict):
        raise ValueError("Brak poprawnego wyniku Centrum.")
    if center == "System":
        if action == "repair":
            operation = str(result.get("operation", ""))
            status = str(result.get("status", "UNKNOWN"))
            if operation not in ("sfc", "dism-scan", "dism-restore", "flush-dns",
                                 "winsock-reset", "dhcp-renew") or status not in ("COMPLETE", "FAILED", "UNKNOWN"):
                raise ValueError("Nieprawidłowy wynik naprawy.")
            return {"diagnoza": f"Naprawa {operation}: {status}; kod wyjścia {result.get('exit_code')}.",
                    "wykonane_czynnosci": f"Uruchomiono {operation} w System Center; brak gwarantowanego cofnięcia."}
        if action == "toolkit":
            sections = result.get("diagnostic", {}).get("sections", {})
            if not isinstance(sections, dict):
                raise ValueError("Nieprawidłowe sekcje diagnostyki.")
            unknown = sum(isinstance(item, dict) and item.get("status") == "UNKNOWN"
                          for item in sections.values())
            return {"diagnoza": f"Diagnostyka aktualizacji Windows: {len(sections)} sekcje, {unknown} UNKNOWN.",
                    "wykonane_czynnosci": "Wykonano odczyt diagnostyczny System Center; nie uruchomiono naprawy."}
        if action == "capture":
            return {"diagnoza": f"Migawka systemu: {int(result.get('unknown', 0))} sekcji UNKNOWN.",
                    "wykonane_czynnosci": "Utworzono migawkę systemu w System Center."}
        if action == "compare":
            sections = result.get("comparison", {}).get("sections", {})
            unknown = sum(isinstance(item, dict) and item.get("status") == "UNKNOWN"
                          for item in sections.values())
            return {"diagnoza": f"Porównanie dwóch migawek: {len(sections)} sekcje, {unknown} UNKNOWN.",
                    "wykonane_czynnosci": "Porównano zapisane migawki w System Center."}
        if action == "scan":
            data = result.get("result", {})
            return {"diagnoza": f"Skan czyszczenia: {len(data.get('files', data.get('items', [])))} pozycji.",
                    "wykonane_czynnosci": "Przeprowadzono analizę bez usuwania plików."}
        if action == "clean":
            data = result.get("result", {})
            return {"diagnoza": f"Przeniesiono do kwarantanny: {int(data.get('moved', 0))} plików.",
                    "wykonane_czynnosci": "Wykonano kontrolowane czyszczenie w System Center."}
        if action == "restore":
            data = result.get("result", {})
            return {"diagnoza": f"Przywrócono z kwarantanny: {int(data.get('restored', 0))} plików.",
                    "wykonane_czynnosci": "Wykonano przywracanie w System Center."}
    if center == "Security":
        data = result.get("data", {})
        if not isinstance(data, dict):
            raise ValueError("Nieprawidłowy wynik Security Center.")
        if action in ("audit", "offline"):
            return {"diagnoza": f"Audyt konfiguracji: wynik {int(data['risk_score'])}/100, "
                    f"{int(data['unknown_checks'])} kontroli UNKNOWN. Wynik nie jest diagnozą infekcji.",
                    "wykonane_czynnosci": "Przeprowadzono odczytowy audyt Security Center."}
        if action in ("triage", "triage_folder", "triage_offline"):
            return {"diagnoza": f"Triage: {len(data.get('alerts', []))} alertów, "
                    f"{len(data.get('unknown_sections', []))} sekcji UNKNOWN. Alerty wymagają oceny.",
                    "wykonane_czynnosci": "Przeprowadzono odczytowy triage Security Center."}
        if action == "file":
            return {"diagnoza": "Przeprowadzono inspekcję wskazanego pliku; wynik wymaga oceny technika.",
                    "wykonane_czynnosci": "Odczytano metadane i hashe pliku bez jego wykonania."}
    raise ValueError("Brak mapowania tego wyniku do raportu serwisowego.")
