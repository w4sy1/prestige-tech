"""Odczyt lokalnego katalogu kopii DNS bez wykonywania zmian."""

import json
from pathlib import Path


def list_dns_backups(directory, *, limit=200):
    folder = Path(directory)
    if not folder.is_dir():
        raise ValueError("Wybierz istniejący katalog kopii DNS.")
    rows = []
    for path in sorted(folder.glob("*.json")):
        if len(rows) >= limit:
            break
        try:
            if not path.is_file() or path.stat().st_size > 1024 * 1024:
                continue
            record = json.loads(path.read_text(encoding="utf-8-sig"))
            if (not isinstance(record, dict) or record.get("schema_version") != 1
                    or record.get("operation") not in ("network-dns-ipv4", "network-dns-ipv6")
                    or not isinstance(record.get("original"), dict)):
                continue
            rows.append({"file": str(path.resolve()), "family": record["operation"].rsplit("-", 1)[-1],
                         "created_utc": str(record.get("created_utc", "")),
                         "status": str(record.get("status", "UNKNOWN")),
                         "interface_index": record["original"].get("index")})
        except (OSError, ValueError, UnicodeError):
            continue
    return rows
