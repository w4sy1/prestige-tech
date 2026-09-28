"""Przyrostowy odczyt logu NetRadar z rotacją i ograniczoną pamięcią."""

from collections import Counter, defaultdict, deque
import hashlib
import ipaddress
from pathlib import Path

from .traffic_analysis import parse_log


class RollingDetector:
    def __init__(self, local_ips, window=60):
        self.local = {str(ipaddress.ip_address(item)) for item in local_ips}
        self.window = window
        self.buckets = defaultdict(deque)
        self.counts = defaultdict(Counter)
        self.last_alert = {}
        self.latest = None
        self.dropped = 0
        self.syn_seen = {}
        self.syn_order = deque()
        self.retransmissions = 0

    def process(self, event):
        timestamp = event["epoch"]
        if self.latest is not None and timestamp < self.latest:
            self.dropped += 1
            return None
        self.latest = timestamp
        while self.syn_order and timestamp - self.syn_order[0][1] > self.window:
            identity, _ = self.syn_order.popleft()
            self.syn_seen.pop(identity, None)
        identity = event.get("syn_id")
        if identity:
            if identity in self.syn_seen:
                self.retransmissions += 1
                return None
            self.syn_seen[identity] = timestamp
            self.syn_order.append((identity, timestamp))
            if len(self.syn_order) > 10000:
                expired, _ = self.syn_order.popleft()
                self.syn_seen.pop(expired, None)
                self.dropped += 1
        if event["dst"] not in self.local or event["protocol"] != "TCP" or event.get("syn") is False:
            return None
        source = event["src"]
        if source not in self.buckets and len(self.buckets) >= 256:
            oldest = min(self.buckets, key=lambda key: self.buckets[key][-1]["epoch"])
            self.dropped += len(self.buckets[oldest])
            del self.buckets[oldest], self.counts[oldest]
            self.last_alert.pop(oldest, None)
        bucket, counts = self.buckets[source], self.counts[source]
        bucket.append(event)
        counts[event["port"]] += 1
        while bucket and (timestamp - bucket[0]["epoch"] > self.window or len(bucket) > 512):
            over_limit = len(bucket) > 512
            old = bucket.popleft()
            counts[old["port"]] -= 1
            if counts[old["port"]] == 0:
                del counts[old["port"]]
            if over_limit:
                self.dropped += 1
        sensitive = any(counts[port] >= 10 for port in (22, 3389, 445))
        if (len(counts) < 10 and not sensitive) or timestamp - self.last_alert.get(source, -1e20) < self.window:
            return None
        classification = "Możliwy skan portów" if len(counts) >= 10 else "Powtarzalne próby SSH/RDP/SMB"
        self.last_alert[source] = timestamp
        identifier = hashlib.sha256(f"{source}|{event['timestamp']}|{classification}".encode()).hexdigest()
        return {"id": identifier, "source": source, "attempts": len(bucket),
                "unique_ports": len(counts), "ports": sorted(counts),
                "classification": classification, "timestamp": event["timestamp"],
                "note": "Heurystyka; może obejmować legalne narzędzia i nie dowodzi ataku."}


class TrafficStream:
    def __init__(self, path, kind, local_ips, *, utc_offset="+00:00", max_bytes=1024 * 1024):
        if kind not in {"jsonl", "windows", "linux"}:
            raise ValueError("Nieobsługiwany format logu.")
        if not 1024 <= max_bytes <= 8 * 1024 * 1024:
            raise ValueError("Limit odczytu jest poza zakresem.")
        self.path = Path(path)
        self.kind, self.local_ips = kind, tuple(local_ips)
        self.utc_offset, self.max_bytes = utc_offset, max_bytes
        self.position = 0
        self.identity = None
        self.header = ""
        self.detector = RollingDetector(self.local_ips)
        self.rotations = 0
        self.rejected = 0

    def poll(self):
        stat = self.path.stat()
        identity = (stat.st_dev, stat.st_ino)
        rotated = self.identity is not None and (identity != self.identity or stat.st_size < self.position)
        if rotated:
            self.position = 0
            self.header = ""
            self.detector = RollingDetector(self.local_ips)
            self.rotations += 1
        self.identity = identity
        new_events = []
        rejected = 0
        bytes_read = 0
        with self.path.open("rb") as stream:
            stream.seek(self.position)
            while bytes_read < self.max_bytes:
                start = stream.tell()
                line = stream.readline(65537)
                if not line:
                    break
                if len(line) > 65536:
                    while line and not line.endswith(b"\n"):
                        line = stream.readline(65537)
                    self.position = stream.tell()
                    rejected += 1
                    break
                if not line.endswith(b"\n"):
                    self.position = start
                    break
                self.position = stream.tell()
                bytes_read += len(line)
                text = line.decode("utf-8-sig", errors="replace")
                if text.startswith("#Fields:"):
                    self.header = text
                    continue
                batch, bad = parse_log((self.header if self.kind == "windows" else "") + text,
                                       self.kind, utc_offset=self.utc_offset)
                new_events.extend(batch)
                rejected += bad
        self.rejected += rejected
        old_dropped = self.detector.dropped
        alerts = [alert for event in sorted(new_events, key=lambda row: row["epoch"])
                  if (alert := self.detector.process(event)) is not None]
        return {"status": "UNKNOWN" if rejected or self.detector.dropped != old_dropped or rotated else "COMPLETE",
                "records": len(new_events), "rejected": rejected, "alerts": alerts,
                "rotations": self.rotations, "position": self.position,
                "note": "Przyrostowy odczyt logu; nie jest przechwytywaniem pakietów."}
