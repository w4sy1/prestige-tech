"""Lokalna historia obserwacji urządzeń LAN bez wnioskowania offline z cache."""

from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import re
import sqlite3


_MAC = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\Z")
LAN_CATEGORIES = ("Moje", "Rodzina", "IoT", "Router", "Nieznane")


def normalize_devices(rows):
    if not isinstance(rows, list):
        raise ValueError("Wymagana lista urządzeń.")
    devices = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Nieprawidłowy wiersz urządzenia.")
        mac = str(row["mac"]).lower().replace("-", ":")
        if not _MAC.fullmatch(mac) or mac == "00:00:00:00:00:00" or int(mac[:2], 16) & 1:
            raise ValueError("Wymagany adres MAC unicast.")
        values = row.get("ips", [row.get("ip")])
        if not isinstance(values, list) or not values:
            raise ValueError("Wymagana lista adresów IP.")
        ips = {str(ipaddress.ip_address(value)) for value in values}
        current = devices.setdefault(mac, {"mac": mac, "ips": [], "hostname": "", "vendor": ""})
        current["ips"] = sorted(set(current["ips"]) | ips,
                                key=lambda value: (ipaddress.ip_address(value).version,
                                                   int(ipaddress.ip_address(value))))
        for field in ("hostname", "vendor"):
            if row.get(field):
                current[field] = str(row[field])[:253]
    return sorted(devices.values(), key=lambda row: row["mac"])


class DeviceHistory:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.database = sqlite3.connect(path)
        self.database.row_factory = sqlite3.Row
        self.database.executescript("""
            CREATE TABLE IF NOT EXISTS devices (
                mac TEXT PRIMARY KEY, ips TEXT NOT NULL, hostname TEXT NOT NULL,
                vendor TEXT NOT NULL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
                status TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Nieznane');
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, mac TEXT NOT NULL,
                event TEXT NOT NULL, details TEXT NOT NULL);
        """)
        columns = {row[1] for row in self.database.execute("PRAGMA table_info(devices)")}
        if "category" not in columns:
            with self.database:
                self.database.execute("ALTER TABLE devices ADD COLUMN category TEXT NOT NULL DEFAULT 'Nieznane'")

    def observe(self, rows, *, complete=False, captured_at=None):
        rows = normalize_devices(rows)
        timestamp = captured_at or datetime.now(timezone.utc).isoformat()
        previous = {row["mac"]: dict(row) for row in self.database.execute("SELECT * FROM devices")}
        events = []
        with self.database:
            for row in rows:
                mac = row["mac"]
                old = previous.get(mac)
                if old is None:
                    changes = ["NEW_DEVICE"]
                else:
                    changes = []
                    if set(json.loads(old["ips"])) != set(row["ips"]):
                        changes.append("IP_CHANGE")
                    if row["hostname"] and old["hostname"] != row["hostname"]:
                        changes.append("HOSTNAME_CHANGE")
                    if old["status"] == "not_observed":
                        changes.append("RETURNED")
                if any(mac != other_mac and set(json.loads(other["ips"])) & set(row["ips"])
                       for other_mac, other in previous.items()):
                    changes.append("POSSIBLE_MAC_CHANGE")
                self.database.execute("""
                    INSERT INTO devices(mac,ips,hostname,vendor,first_seen,last_seen,status)
                    VALUES(?,?,?,?,?,?,'observed')
                    ON CONFLICT(mac) DO UPDATE SET ips=excluded.ips,
                        hostname=CASE WHEN excluded.hostname='' THEN devices.hostname ELSE excluded.hostname END,
                        vendor=CASE WHEN excluded.vendor='' THEN devices.vendor ELSE excluded.vendor END,
                        last_seen=excluded.last_seen,status='observed'
                """, (mac, json.dumps(row["ips"]), row["hostname"], row["vendor"], timestamp, timestamp))
                events.extend({"mac": mac, "event": event, "details": ", ".join(row["ips"])}
                              for event in changes)
            if complete:
                current = {row["mac"] for row in rows}
                for mac, old in previous.items():
                    if mac not in current and old["status"] != "not_observed":
                        self.database.execute("UPDATE devices SET status='not_observed' WHERE mac=?", (mac,))
                        events.append({"mac": mac, "event": "NOT_OBSERVED",
                                       "details": "Brak w oznaczonej kompletnej obserwacji; nie dowodzi offline."})
            self.database.executemany(
                "INSERT INTO events(timestamp,mac,event,details) VALUES(?,?,?,?)",
                [(timestamp, row["mac"], row["event"], row["details"]) for row in events]
            )
        return {"observed": len(rows), "events": events, "complete": complete,
                "note": "Wpis cache lub odpowiedź ICMP nie potwierdza trwałej obecności urządzenia."}

    def devices(self):
        return [dict(row, ips=json.loads(row["ips"])) for row in
                self.database.execute("SELECT * FROM devices ORDER BY mac")]

    def tag_device(self, mac, category):
        mac = str(mac).lower().replace("-", ":")
        if not _MAC.fullmatch(mac) or category not in LAN_CATEGORIES:
            raise ValueError("Nieprawidłowy MAC lub kategoria urządzenia.")
        with self.database:
            cursor = self.database.execute("UPDATE devices SET category=? WHERE mac=?", (category, mac))
            if cursor.rowcount != 1:
                raise ValueError("Urządzenia nie ma w lokalnej historii.")
        return {"mac": mac, "category": category}

    def history(self, limit=500):
        if not 1 <= limit <= 10000:
            raise ValueError("Niedozwolony limit historii.")
        return [dict(row) for row in self.database.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))]

    def close(self):
        self.database.close()
