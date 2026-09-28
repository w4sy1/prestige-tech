"""Historia obserwacji Monitora, zapisywana wyłącznie na żądanie użytkownika."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path


KINDS = {"added": "Nowy", "removed": "Usunięty", "changed": "Zmieniony"}


def new_history(root):
    return {"schema_version": 1, "root": str(Path(root).resolve()), "events": []}


def append_comparison(history, result, *, observed_at=None):
    if result.get("status") != "COMPLETE":
        raise ValueError("Nie wolno zapisywać zdarzeń z niepełnego porównania.")
    stamp = observed_at or datetime.now(timezone.utc).isoformat()
    for key, label in KINDS.items():
        for path in result[key]:
            history["events"].append({"at_utc": stamp, "path": path, "kind": label})
    for row in result.get("renamed", []):
        history["events"].append({"at_utc": stamp, "path": row["path"],
                                  "old_path": row["old_path"], "kind": "Zmieniono nazwę"})
    return history


def validate_history(history):
    if (not isinstance(history, dict) or history.get("schema_version") != 1
            or not isinstance(history.get("root"), str)
            or not isinstance(history.get("events"), list)):
        raise ValueError("Nieobsługiwany format historii.")
    for row in history["events"]:
        if (not isinstance(row, dict) or not isinstance(row.get("at_utc"), str)
                or not isinstance(row.get("path"), str)
                or row.get("kind") not in {*KINDS.values(), "Zmieniono nazwę"}
                or (row.get("kind") == "Zmieniono nazwę"
                    and not isinstance(row.get("old_path"), str))):
            raise ValueError("Nieprawidłowe zdarzenie w historii.")
    return history


def save_history(history, destination):
    validate_history(history)
    path = Path(destination)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(history, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return path


def load_history(source):
    return validate_history(json.loads(Path(source).read_text(encoding="utf-8")))


class EventJournal:
    """Dopisuj zatwierdzone zdarzenia do nowego pliku poza obserwowanym katalogiem."""

    def __init__(self, history, destination):
        validate_history(history)
        path = Path(destination).resolve()
        root = Path(history["root"]).resolve()
        if path.is_relative_to(root):
            raise ValueError("Dziennik musi być poza obserwowanym katalogiem.")
        self.path = path
        self.stream = path.open("x", encoding="utf-8")
        try:
            self._write({"schema_version": 1, "root": history["root"]})
            for row in history["events"]:
                self._write(row)
        except BaseException:
            self.stream.close()
            raise

    def _write(self, row):
        self.stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def append(self, rows):
        for row in rows:
            self._write(row)

    def close(self):
        self.stream.close()


def load_journal(source):
    with Path(source).open("r", encoding="utf-8") as stream:
        header = json.loads(stream.readline())
        history = {"schema_version": header.get("schema_version"),
                   "root": header.get("root"), "events": []}
        for line in stream:
            history["events"].append(json.loads(line))
    return validate_history(history)
