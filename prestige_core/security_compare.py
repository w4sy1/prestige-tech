"""Porównanie odczytowych audytów Security Check."""

from prestige_core.security_rules import CHECK_NAMES


def compare_audits(before, after):
    if not isinstance(before.get("coverage"), dict) or not isinstance(after.get("coverage"), dict):
        raise ValueError("Wymagane dwa wyniki audytu Security Check.")
    rows = []
    for name in CHECK_NAMES:
        old = before["coverage"].get(name, "UNKNOWN")
        new = after["coverage"].get(name, "UNKNOWN")
        if old != new:
            rows.append({"check": name, "before": old, "after": new})
    return {"status": "COMPLETE" if before.get("unknown_checks") == after.get("unknown_checks") == 0
            else "UNKNOWN", "coverage_changes": rows,
            "risk_score_before": before.get("risk_score"),
            "risk_score_after": after.get("risk_score"),
            "alert_count_before": before.get("alerts_total"),
            "alert_count_after": after.get("alerts_total"),
            "note": "Zmiana wyniku nie dowodzi usunięcia zagrożenia; porównaj zakres odczytów i dowody."}
