"""Metadane TShark ARP/TCP/UDP/ICMP bez przechowywania payloadu."""

from collections import defaultdict, deque
import ipaddress
import math
import os
import queue
import re
import shutil
import subprocess
import threading
import time


FIELDS = ("frame.time_epoch", "eth.src", "ip.src", "ip.dst", "tcp.srcport",
          "tcp.dstport", "tcp.flags.syn", "tcp.flags.ack", "udp.srcport",
          "udp.dstport", "icmp.type", "arp.src.proto_ipv4", "arp.dst.proto_ipv4")
_INTERFACE = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$")


def parse_line(line):
    parts = line.rstrip("\r\n").split("|")
    if len(parts) != len(FIELDS):
        raise ValueError("Niepełny wiersz TShark.")
    try:
        epoch = float(parts[0])
        if not math.isfinite(epoch) or epoch < 0:
            raise ValueError
        def address(value):
            return str(ipaddress.IPv4Address(value)) if value else None
        source, destination = address(parts[2]), address(parts[3])
        arp_source, arp_target = address(parts[11]), address(parts[12])
        tcp_port = int(parts[5]) if parts[5] else None
        udp_port = int(parts[9]) if parts[9] else None
        icmp_type = int(parts[10]) if parts[10] else None
        if any(port is not None and not 1 <= port <= 65535 for port in (tcp_port, udp_port)):
            raise ValueError
    except (ValueError, ipaddress.AddressValueError) as error:
        raise ValueError("Nieprawidłowe pola metadanych TShark.") from error
    if arp_source and arp_target:
        return {"epoch": epoch, "protocol": "ARP", "src": arp_source,
                "target": arp_target, "mac": parts[1].lower() or None}
    if source and destination and tcp_port:
        return {"epoch": epoch, "protocol": "TCP", "src": source, "dst": destination,
                "port": tcp_port, "syn": parts[6] == "1", "ack": parts[7] == "1"}
    if source and destination and udp_port:
        return {"epoch": epoch, "protocol": "UDP", "src": source, "dst": destination,
                "port": udp_port}
    if source and destination and icmp_type is not None:
        return {"epoch": epoch, "protocol": "ICMP", "src": source,
                "dst": destination, "icmp_type": icmp_type}
    return None


class DeepDetector:
    def __init__(self, local_ips=()):
        self.local = {str(ipaddress.IPv4Address(item)) for item in local_ips}
        self.traffic = defaultdict(deque)
        self.arp = defaultdict(deque)
        self.last_alert = {}
        self.dropped = 0

    def process(self, event):
        source = event["src"]
        if source in self.local:
            return None
        if source not in self.traffic and source not in self.arp and len(self.traffic) + len(self.arp) >= 256:
            self.dropped += 1
            return None
        epoch = event["epoch"]
        if event["protocol"] == "ARP":
            rows, window = self.arp[source], 10
            rows.append(event)
            while rows and epoch - rows[0]["epoch"] > window:
                rows.popleft()
            while len(rows) > 512:
                rows.popleft()
            count = len({row["target"] for row in rows})
            if count < 18:
                return None
            category, severity = "ARP sweep", "HIGH"
        else:
            rows, window = self.traffic[source], 30
            rows.append(event)
            while rows and epoch - rows[0]["epoch"] > window:
                rows.popleft()
            while len(rows) > 512:
                rows.popleft()
            tcp = [row for row in rows if row["protocol"] == "TCP" and row.get("syn") and not row.get("ack")]
            udp = [row for row in rows if row["protocol"] == "UDP"]
            icmp = [row for row in rows if row["protocol"] == "ICMP"]
            tcp_ports = {row["port"] for row in tcp}
            udp_ports = {row["port"] for row in udp}
            if len(tcp_ports) >= 30:
                category, severity = "TCP port sweep", "HIGH"
            elif len(tcp_ports) >= 12:
                category, severity = "Podejrzane skanowanie TCP", "MEDIUM"
            elif len(udp_ports) >= 12:
                category, severity = "UDP port sweep", "MEDIUM"
            elif len(icmp) >= 20:
                category, severity = "ICMP burst / sweep", "MEDIUM"
            elif len(rows) >= 35 and len(tcp_ports | udp_ports) <= 3:
                category, severity = "Powtarzane próby połączenia", "MEDIUM"
            else:
                return None
            count = len(rows)
        key = (source, category)
        if epoch - self.last_alert.get(key, -1e20) < 20:
            return None
        self.last_alert[key] = epoch
        return {"source": source, "category": category, "severity": severity,
                "attempts": count, "epoch": epoch,
                "note": "Heurystyka z metadanych; nie dowodzi ataku ani nie identyfikuje osoby."}


def list_interfaces(*, executable=None, runner=subprocess.run):
    executable = executable or shutil.which("tshark")
    if not executable:
        raise FileNotFoundError("Brak TShark. Zainstaluj Wireshark/TShark i Npcap.")
    result = runner([executable, "-D"], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=15, check=False)
    if result.returncode:
        raise RuntimeError("TShark nie zwrócił listy interfejsów.")
    rows = []
    for line in result.stdout.splitlines():
        match = _INTERFACE.match(line)
        if match:
            rows.append({"index": int(match.group(1)), "label": match.group(2)})
    if not rows:
        raise RuntimeError("TShark nie widzi interfejsów przechwytywania.")
    return rows


def capture(interface, *, seconds=30, local_ips=(), cancel_event=None,
            on_alert=None, executable=None, launcher=subprocess.Popen, clock=time.monotonic,
            platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Deep Capture wymaga Windows i Npcap.")
    if type(interface) is not int or not 1 <= interface <= 9999 or not 1 <= seconds <= 300:
        raise ValueError("Wybierz indeks interfejsu i czas 1–300 s.")
    executable = executable or shutil.which("tshark")
    if not executable:
        raise FileNotFoundError("Brak TShark. Zainstaluj Wireshark/TShark i Npcap.")
    command = [executable, "-i", str(interface), "-l", "-n", "-f", "arp or tcp or udp or icmp",
               "-T", "fields"]
    for field in FIELDS:
        command.extend(("-e", field))
    command.extend(("-E", "separator=|"))
    process = launcher(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                       text=True, encoding="utf-8", errors="replace", bufsize=1,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    incoming = queue.Queue(maxsize=10000)
    overflow = threading.Event()
    reader_done = threading.Event()
    def reader():
        try:
            for line in process.stdout:
                try:
                    incoming.put_nowait(line)
                except queue.Full:
                    overflow.set()
                    break
        finally:
            reader_done.set()
    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    detector = DeepDetector(local_ips)
    packets = rejected = 0
    alerts = []
    status = "COMPLETE"
    deadline = clock() + seconds
    try:
        while clock() < deadline:
            if overflow.is_set():
                status = "UNKNOWN"
                break
            if cancel_event is not None and cancel_event.is_set():
                status = "CANCELLED"
                break
            try:
                line = incoming.get(timeout=0.2)
            except queue.Empty:
                if reader_done.is_set() and incoming.empty():
                    status = "UNKNOWN"
                    break
                continue
            try:
                event = parse_line(line)
            except ValueError:
                rejected += 1
                continue
            if event is None:
                continue
            packets += 1
            alert = detector.process(event)
            if alert is not None:
                if len(alerts) >= 1000:
                    status = "UNKNOWN"
                    break
                alerts.append(alert)
                if on_alert is not None:
                    on_alert(alert)
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        thread.join(timeout=2)
    if (rejected or overflow.is_set() or detector.dropped) and status == "COMPLETE":
        status = "UNKNOWN"
    return {"status": status, "packets": packets, "rejected": rejected,
            "dropped_sources": detector.dropped, "alerts": alerts,
            "note": "Metadane bez payloadu; błędne wiersze lub przepełnienie oznaczają UNKNOWN."}
