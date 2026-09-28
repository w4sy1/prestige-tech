"""Trwały stan polling Monitora w SQLite, poza katalogiem źródłowym."""

import json
from pathlib import Path
import sqlite3

from .event_history import append_comparison, new_history


class WatchStateStore:
    def __init__(self, root, database):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Wymagany katalog do obserwacji.")
        self.path = Path(database).resolve()
        if self.path.is_relative_to(self.root):
            raise ValueError("Baza SQLite musi być poza obserwowanym katalogiem.")
        existing = self.path.exists()
        self.connection = sqlite3.connect(self.path)
        try:
            version = self.connection.execute("PRAGMA user_version").fetchone()[0]
            if existing:
                tables = {row[0] for row in self.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'")}
                if version != 1 or not {"metadata", "state", "events"}.issubset(tables):
                    raise ValueError("Istniejąca baza nie ma formatu Monitora; wybierz nowy plik.")
            with self.connection:
                self.connection.execute("CREATE TABLE IF NOT EXISTS metadata (root TEXT NOT NULL)")
                self.connection.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK (id = 1), snapshot TEXT NOT NULL)")
                self.connection.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, at_utc TEXT NOT NULL, kind TEXT NOT NULL, path TEXT NOT NULL, old_path TEXT)")
                owner = self.connection.execute("SELECT root FROM metadata LIMIT 1").fetchone()
                if owner and owner[0] != str(self.root):
                    raise ValueError("Ta baza należy do innego katalogu.")
                if existing and owner is None:
                    raise ValueError("Istniejąca baza nie ma właściciela Monitora.")
                if owner is None:
                    self.connection.execute("INSERT INTO metadata(root) VALUES (?)", (str(self.root),))
                self.connection.execute("PRAGMA user_version = 1")
        except BaseException:
            self.connection.close()
            raise

    def load(self):
        row = self.connection.execute("SELECT snapshot FROM state WHERE id = 1").fetchone()
        if row is None:
            return None
        snapshot = json.loads(row[0])
        if (snapshot.get("schema_version") != 1 or snapshot.get("root") != str(self.root)
                or not snapshot.get("complete") or not isinstance(snapshot.get("files"), list)):
            raise ValueError("Baza zawiera nieprawidłową lub niepełną migawkę.")
        return snapshot

    def record(self, snapshot, result=None):
        if (snapshot.get("schema_version") != 1 or snapshot.get("root") != str(self.root)
                or not snapshot.get("complete")):
            raise ValueError("Nie wolno zapisać niepełnej lub obcej migawki.")
        if result is not None and result.get("status") != "COMPLETE":
            raise ValueError("Nie wolno zapisać niepełnego porównania.")
        history = new_history(self.root)
        if result is not None:
            append_comparison(history, result)
        with self.connection:
            self.connection.execute("INSERT OR REPLACE INTO state(id, snapshot) VALUES (1, ?)",
                                    (json.dumps(snapshot, ensure_ascii=False),))
            self.connection.executemany(
                "INSERT INTO events(at_utc, kind, path, old_path) VALUES (?, ?, ?, ?)",
                [(row["at_utc"], row["kind"], row["path"], row.get("old_path"))
                 for row in history["events"]],
            )
        return history["events"]

    def load_events(self):
        rows = self.connection.execute(
            "SELECT at_utc, kind, path, old_path FROM events ORDER BY id"
        ).fetchall()
        return [{"at_utc": stamp, "kind": kind, "path": path,
                 **({"old_path": old_path} if old_path is not None else {})}
                for stamp, kind, path, old_path in rows]

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
