"""Opcjonalna lokalna historia wyników benchmarku DNS bez treści zapytań."""

from datetime import datetime, timezone
import ipaddress
import math
from pathlib import Path
import sqlite3
import uuid


class DnsHistory:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, captured_utc TEXT NOT NULL,
            server TEXT NOT NULL, samples INTEGER NOT NULL, successful INTEGER NOT NULL,
            mean_ms REAL, error_rate REAL NOT NULL)""")
        self.db.commit()

    def record(self, benchmark):
        if not isinstance(benchmark, dict) or not isinstance(benchmark.get("ranking"), list):
            raise ValueError("Nieprawidłowy wynik benchmarku DNS.")
        rows = []
        for item in benchmark["ranking"]:
            if not isinstance(item, dict):
                raise ValueError("Nieprawidłowy wiersz benchmarku DNS.")
            try:
                server = str(ipaddress.ip_address(item["server"]))
                count = int(item["count"])
                successful = int(item["successful"])
                error_rate = float(item["error_rate"])
                mean = None if item.get("mean_ms") is None else float(item["mean_ms"])
                if (not 1 <= count <= 500 or not 0 <= successful <= count
                        or not math.isfinite(error_rate) or not 0 <= error_rate <= 1):
                    raise ValueError
                if mean is not None and (not math.isfinite(mean) or not 0 <= mean <= 60000):
                    raise ValueError
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("Nieprawidłowe statystyki benchmarku DNS.") from error
            rows.append((server, count, successful, mean, error_rate))
        if not 1 <= len(rows) <= 16:
            raise ValueError("Wynik benchmarku ma nieprawidłową liczbę resolverów.")
        run_id = uuid.uuid4().hex
        stamp = datetime.now(timezone.utc).isoformat()
        with self.db:
            self.db.executemany(
                "INSERT INTO results(run_id,captured_utc,server,samples,successful,mean_ms,error_rate) "
                "VALUES(?,?,?,?,?,?,?)",
                [(run_id, stamp, *row) for row in rows])
            self.db.execute("""DELETE FROM results WHERE id NOT IN
                (SELECT id FROM results ORDER BY id DESC LIMIT 1000)""")
        return {"run_id": run_id, "saved": len(rows)}

    def recent(self, limit=50):
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("Limit historii DNS poza zakresem.")
        return [dict(row) for row in self.db.execute(
            "SELECT run_id,captured_utc,server,samples,successful,mean_ms,error_rate "
            "FROM results ORDER BY id DESC LIMIT ?", (limit,))]

    def close(self):
        self.db.close()
