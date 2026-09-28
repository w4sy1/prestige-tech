"""Odczyt logów NetRadar i heurystyka prób portów bez przechwytywania pakietów."""

from collections import defaultdict, deque
from datetime import datetime
import hashlib
import ipaddress
import json
from pathlib import Path
import re


def parse_log(text, kind, *, utc_offset="+00:00"):
    if kind not in {"jsonl", "windows", "linux"}:
        raise ValueError("Nieobsługiwany format logu.")
    events, rejected, fields = [], 0, []
    for line in text.splitlines():
        if line.startswith("#Fields:"):
            fields = line.split(":", 1)[1].split()
            continue
        if not line.strip() or line.startswith("#"):
            continue
        try:
            if kind == "jsonl":
                row = json.loads(line)
            elif kind == "windows":
                record = dict(zip(fields, line.split()))
                flags = record.get("tcpflags", "-")
                row = {"timestamp": record["date"] + "T" + record["time"] + utc_offset,
                       "src": record["src-ip"], "dst": record["dst-ip"],
                       "port": int(record["dst-port"]), "protocol": record["protocol"],
                       "syn": "S" in flags if flags != "-" else None}
            else:
                record = dict(re.findall(r"\b(SRC|DST|DPT|PROTO)=([^\s]+)", line))
                row = {"timestamp": line.split()[0], "src": record["SRC"],
                       "dst": record["DST"], "port": int(record["DPT"]),
                       "protocol": record["PROTO"],
                       "syn": True if re.search(r"\bSYN\b", line) else
                       False if re.search(r"\b(?:ACK|FIN|RST)\b", line) else None}
            if not isinstance(row, dict) or (row.get("syn") is not None and type(row["syn"]) is not bool):
                raise ValueError("Nieprawidłowy rekord SYN.")
            stamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("Czas musi mieć strefę.")
            src = str(ipaddress.ip_address(row["src"]))
            dst = str(ipaddress.ip_address(row["dst"]))
            port = int(row["port"])
            if not 1 <= port <= 65535:
                raise ValueError("Port poza zakresem.")
            events.append({"timestamp": stamp.isoformat(), "epoch": stamp.timestamp(),
                           "src": src, "dst": dst, "port": port,
                           "protocol": str(row["protocol"]).upper(), "syn": row.get("syn"),
                           "syn_id": row.get("syn_id")})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            rejected += 1
    return sorted(events, key=lambda row: row["epoch"]), rejected


def detect_attempts(events, local_ips, *, whitelist=(), window=60):
    if not 1 <= window <= 3600:
        raise ValueError("Okno analizy poza zakresem.")
    local = {str(ipaddress.ip_address(address)) for address in local_ips}
    networks = [ipaddress.ip_network(value, strict=False) for value in whitelist]
    buckets = defaultdict(deque)
    last_alert = {}
    alerts = []
    seen_syn_ids = set()
    dropped = 0
    for event in sorted(events, key=lambda row: row["epoch"]):
        source = ipaddress.ip_address(event["src"])
        if event["dst"] not in local or any(source in network for network in networks):
            continue
        if event["protocol"] != "TCP" or event.get("syn") is False:
            continue
        identity = event.get("syn_id")
        if identity:
            if identity in seen_syn_ids:
                continue
            seen_syn_ids.add(identity)
            if len(seen_syn_ids) > 100000:
                seen_syn_ids.clear()
                dropped += 1
        address = str(source)
        bucket = buckets[address]
        bucket.append(event)
        while bucket and event["epoch"] - bucket[0]["epoch"] > window:
            bucket.popleft()
        while len(bucket) > 10000:
            bucket.popleft()
            dropped += 1
        ports = {row["port"] for row in bucket}
        sensitive = any(sum(row["port"] == port for row in bucket) >= 10
                        for port in (22, 3389, 445))
        if (len(ports) >= 10 or sensitive) and event["epoch"] - last_alert.get(address, -1e20) >= window:
            classification = "Możliwy skan portów" if len(ports) >= 10 else "Powtarzalne próby SSH/RDP/SMB"
            identifier = hashlib.sha256(f"{address}|{event['timestamp']}|{classification}".encode()).hexdigest()
            alerts.append({"id": identifier, "source": address, "attempts": len(bucket),
                           "unique_ports": len(ports), "ports": sorted(ports),
                           "classification": classification, "timestamp": event["timestamp"],
                           "note": "Heurystyka; może obejmować legalne narzędzia i nie dowodzi ataku."})
            last_alert[address] = event["epoch"]
    return {"alerts": alerts, "dropped": dropped,
            "note": "Analiza logów, bez live capture; brak alertu nie oznacza braku ruchu."}


def analyze_log(path, kind, local_ips, *, whitelist=(), utc_offset="+00:00"):
    path = Path(path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Log przekracza limit 32 MiB; użyj mniejszego fragmentu.")
    events, rejected = parse_log(path.read_text(encoding="utf-8-sig", errors="replace"),
                                 kind, utc_offset=utc_offset)
    result = detect_attempts(events, local_ips, whitelist=whitelist)
    return {**result, "records": len(events), "rejected": rejected,
            "status": "UNKNOWN" if rejected or result["dropped"] else "COMPLETE"}
