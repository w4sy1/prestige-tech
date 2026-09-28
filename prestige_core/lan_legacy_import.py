"""Jednorazowy import bazy LAN Radar do nowego pliku bez zmiany źródła."""

import ipaddress
import json
from contextlib import closing
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote


_MAC = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\Z")


def import_legacy_lan(source_path, destination_path):
    source, destination = Path(source_path).resolve(), Path(destination_path).resolve()
    if source == destination or not source.is_file() or destination.exists():
        raise ValueError("Źródło musi istnieć, a nowa baza docelowa nie może już istnieć.")
    uri = "file:" + quote(source.as_posix(), safe="/:" ) + "?mode=ro"
    rows = []
    events = []
    with closing(sqlite3.connect(uri, uri=True)) as old:
        old.row_factory = sqlite3.Row
        names = {row[0] for row in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"devices", "events"} <= names:
            raise ValueError("To nie jest baza LAN Radar z tabelami devices i events.")
        columns = {row[1] for row in old.execute("PRAGMA table_info(devices)")}
        required = {"mac", "ip", "hostname", "vendor", "first_seen", "last_seen", "status"}
        if not required <= columns:
            raise ValueError("Baza LAN Radar ma niezgodny schemat urządzeń.")
        for raw in old.execute("SELECT * FROM devices"):
            mac = str(raw["mac"] or "").lower().replace("-", ":")
            if not _MAC.fullmatch(mac) or int(mac[:2], 16) & 1:
                raise ValueError("Nieprawidłowy MAC w starej bazie; import przerwany.")
            try:
                ips = json.loads(raw["ips"]) if "ips" in columns and raw["ips"] else []
                if not ips and raw["ip"]:
                    ips = [raw["ip"]]
                ips = sorted({str(ipaddress.ip_address(ip)) for ip in ips})
            except (TypeError, ValueError) as error:
                raise ValueError("Nieprawidłowy adres IP w starej bazie; import przerwany.") from error
            if not ips:
                raise ValueError("Urządzenie bez adresu IP; import przerwany.")
            rows.append((mac, json.dumps(ips), str(raw["hostname"] or ""),
                         str(raw["vendor"] or ""), str(raw["first_seen"] or ""),
                         str(raw["last_seen"] or ""),
                         "not_observed" if raw["status"] == "offline" else "observed",
                         str(raw["category"] or "") if "category" in columns else ""))
        event_columns = {row[1] for row in old.execute("PRAGMA table_info(events)")}
        if not {"timestamp", "mac", "event", "details"} <= event_columns:
            raise ValueError("Baza LAN Radar ma niezgodny schemat zdarzeń.")
        for raw in old.execute("SELECT timestamp,mac,event,details FROM events ORDER BY id"):
            events.append((str(raw["timestamp"] or ""), str(raw["mac"] or ""),
                           "LEGACY_" + str(raw["event"] or "UNKNOWN"), str(raw["details"] or "")))
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(destination)) as new:
            with new:
                new.executescript("""
                CREATE TABLE devices(mac TEXT PRIMARY KEY,ips TEXT NOT NULL,hostname TEXT NOT NULL,
                    vendor TEXT NOT NULL,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,
                    status TEXT NOT NULL,category TEXT NOT NULL);
                CREATE TABLE events(id INTEGER PRIMARY KEY,timestamp TEXT NOT NULL,mac TEXT NOT NULL,
                    event TEXT NOT NULL,details TEXT NOT NULL);
                """)
                new.executemany("INSERT INTO devices VALUES(?,?,?,?,?,?,?,?)", rows)
                new.executemany("INSERT INTO events(timestamp,mac,event,details) VALUES(?,?,?,?)", events)
    except (OSError, sqlite3.Error):
        destination.unlink(missing_ok=True)
        raise
    return {"devices": len(rows), "events": len(events), "source": str(source),
            "destination": str(destination), "note": "Stare statusy offline oznaczono not_observed; nie są dowodem odłączenia."}
