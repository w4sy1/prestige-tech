"""Jednorazowy, odczytowy import bazy starego Prestige Folder Watch."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import sqlite3
import uuid

from .watch_state import WatchStateStore


_EVENT_KINDS = {"create": "Nowy", "modify": "Zmieniony", "delete": "Usunięty",
                "rename": "Zmieniono nazwę"}
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")


def _relative(value):
    if not isinstance(value, str) or not value:
        raise ValueError("Pusta ścieżka w starej bazie.")
    path = PureWindowsPath(value)
    if path.is_absolute() or path.drive or any(part in {"..", "."} for part in path.parts):
        raise ValueError("Ścieżka poza katalogiem źródłowym w starej bazie.")
    return path.as_posix()


def read_legacy_watch_database(source, root):
    root = Path(root).resolve(strict=True)
    source = Path(source)
    if source.is_symlink() or not source.is_file() or source.resolve().is_relative_to(root):
        raise ValueError("Stara baza musi być zwykłym plikiem poza obserwowanym katalogiem.")
    connection = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"metadata", "state", "events"}.issubset(names):
            raise ValueError("Nieznany schemat starej bazy Folder Watch.")
        owner = connection.execute("SELECT root FROM metadata LIMIT 1").fetchone()
        if owner is None or Path(owner[0]).resolve() != root:
            raise ValueError("Stara baza dotyczy innego katalogu.")
        files = []
        seen = set()
        for name, raw in connection.execute("SELECT path, data FROM state"):
            relative = _relative(name)
            if relative in seen:
                raise ValueError("Duplikat ścieżki w starej bazie.")
            seen.add(relative)
            row = json.loads(raw)
            if (not isinstance(row, dict) or type(row.get("size")) is not int or row["size"] < 0
                    or type(row.get("mtime_ns")) is not int
                    or not isinstance(row.get("sha256"), str)
                    or not _SHA256.fullmatch(row["sha256"])):
                raise ValueError("Nieprawidłowy wpis pliku w starej bazie.")
            files.append({"path": relative, "size": row["size"],
                          "mtime_ns": row["mtime_ns"], "sha256": row["sha256"],
                          "inode": row.get("inode", 0) if type(row.get("inode", 0)) is int else 0})
        events = []
        for stamp, kind, path, old_path in connection.execute(
                "SELECT timestamp, type, path, old_path FROM events ORDER BY id"):
            if kind not in _EVENT_KINDS or not isinstance(stamp, str) or not stamp:
                raise ValueError("Nieprawidłowe zdarzenie w starej bazie.")
            event = {"at_utc": stamp, "kind": _EVENT_KINDS[kind], "path": _relative(path)}
            if kind == "rename":
                event["old_path"] = _relative(old_path)
            events.append(event)
    finally:
        connection.close()
    snapshot = {"schema_version": 1, "root": str(root),
                "captured_at_utc": None,
                "imported_at_utc": datetime.now(timezone.utc).isoformat(),
                "capture_time_unknown": True,
                "files": sorted(files, key=lambda row: row["path"]),
                "errors": [], "complete": True}
    return snapshot, events


def import_legacy_watch_database(source, root, destination):
    snapshot, events = read_legacy_watch_database(source, root)
    target = Path(destination)
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    if target.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError("Nowa baza musi być poza obserwowanym katalogiem.")
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    created = False
    try:
        with WatchStateStore(root, temporary) as store:
            store.record(snapshot)
            with store.connection:
                store.connection.executemany(
                    "INSERT INTO events(at_utc, kind, path, old_path) VALUES (?, ?, ?, ?)",
                    [(row["at_utc"], row["kind"], row["path"], row.get("old_path"))
                     for row in events],
                )
        with temporary.open("rb") as original, target.open("xb") as output:
            created = True
            shutil.copyfileobj(original, output)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)
    return {"destination": str(target.resolve()), "files": len(snapshot["files"]),
            "events": len(events)}
