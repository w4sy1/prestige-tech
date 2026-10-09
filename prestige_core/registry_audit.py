"""Zbiorczy odczyt katalogu Registry bez utrwalania wartości."""

from collections import Counter

from .registry_read import read_operation


def audit_catalog(catalog, *, registry=None, platform=None, cancel_event=None,
                  on_progress=None):
    operations = tuple(catalog)
    if not operations or len(operations) > 5000 or len({item.id for item in operations}) != len(operations):
        raise ValueError("Nieprawidłowy katalog operacji Registry.")
    counts = Counter()
    details = Counter()
    errors = []
    for index, operation in enumerate(operations, 1):
        if cancel_event is not None and cancel_event.is_set():
            return {"status": "CANCELLED", "total": len(operations), "processed": index - 1,
                    "counts": dict(counts), "details": dict(details), "errors": errors,
                    "note": "Odczyt przerwany; wartości nie zostały zapisane."}
        try:
            result = read_operation(operation, registry=registry, platform=platform,
                                    catalog=operations)
            counts[result["status"]] += 1
            details[result.get("reason_code", "UNKNOWN")] += 1
        except (OSError, ValueError, RuntimeError) as error:
            counts["ERROR"] += 1
            details["ERROR"] += 1
            errors.append({"operation": operation.id, "type": type(error).__name__})
        if on_progress is not None:
            on_progress(index, len(operations))
    return {"status": "UNKNOWN" if errors else "COMPLETE", "total": len(operations),
            "processed": len(operations), "counts": dict(counts), "details": dict(details), "errors": errors,
            "note": "Podsumowanie bez wartości rejestru; Niedostępne może oznaczać brak ustawienia."}
