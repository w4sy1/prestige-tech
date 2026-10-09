"""Filtrowanie zapisanych zdarzeń Monitora bez zmiany baseline."""

from datetime import datetime, timezone


def _instant(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Granice czasu muszą zawierać strefę (np. Z).")
    return parsed.astimezone(timezone.utc)


def filter_events(events, *, path="", kind="Wszystkie", start="", end=""):
    beginning, ending = _instant(start), _instant(end)
    if beginning and ending and beginning > ending:
        raise ValueError("Początek okresu jest późniejszy niż koniec.")
    needle = path.casefold()
    result = []
    for row in events:
        stamp = _instant(row["at_utc"])
        if ((not beginning or stamp >= beginning) and (not ending or stamp <= ending)
                and (kind == "Wszystkie" or row["kind"] == kind)
                and (needle in row["path"].casefold()
                     or needle in row.get("old_path", "").casefold())):
            result.append(row)
    return result


def compare_periods(events, first_start, first_end, second_start, second_end):
    first = filter_events(events, start=first_start, end=first_end)
    second = filter_events(events, start=second_start, end=second_end)
    a_end, b_start = _instant(first_end), _instant(second_start)
    if not all((first_start, first_end, second_start, second_end)) or a_end >= b_start:
        raise ValueError("Podaj dwa rozłączne okresy UTC w kolejności chronologicznej.")
    def summary(rows):
        return {"events": len(rows), "by_kind": {kind: sum(row["kind"] == kind for row in rows)
                for kind in sorted({row["kind"] for row in rows})}}
    return {"status": "COMPARED", "first": summary(first), "second": summary(second),
            "note": "Porównano tylko zapisane zdarzenia; brak wpisu nie dowodzi braku zmian. Baseline pozostaje bez zmian."}
