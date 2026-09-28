import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from prestige_core.device_history import DeviceHistory
from prestige_core.lan_legacy_import import import_legacy_lan


class LanLegacyImportTest(unittest.TestCase):
    def test_import_preserves_source_and_history(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "legacy.sqlite"
            dest = Path(folder) / "new.sqlite"
            with closing(sqlite3.connect(source)) as db:
                with db:
                    db.executescript("""CREATE TABLE devices(mac TEXT PRIMARY KEY,ip TEXT,ips TEXT,
                    hostname TEXT,vendor TEXT,first_seen TEXT,last_seen TEXT,status TEXT,category TEXT);
                    CREATE TABLE events(id INTEGER PRIMARY KEY,timestamp TEXT,mac TEXT,event TEXT,details TEXT);""")
                    db.execute("INSERT INTO devices VALUES(?,?,?,?,?,?,?,?,?)",
                               ("00:11:22:33:44:55", "192.0.2.3", '["192.0.2.3"]', "host",
                                "vendor", "first", "last", "offline", "Moje"))
                    db.execute("INSERT INTO events(timestamp,mac,event,details) VALUES(?,?,?,?)",
                               ("time", "00:11:22:33:44:55", "DISAPPEARED", "old"))
            before = source.read_bytes()
            result = import_legacy_lan(source, dest)
            self.assertEqual(result["devices"], 1)
            self.assertEqual(source.read_bytes(), before)
            history = DeviceHistory(dest)
            self.assertEqual(history.devices()[0]["status"], "not_observed")
            self.assertEqual(history.history()[0]["event"], "LEGACY_DISAPPEARED")
            history.close()
            with self.assertRaises(ValueError):
                import_legacy_lan(source, dest)
