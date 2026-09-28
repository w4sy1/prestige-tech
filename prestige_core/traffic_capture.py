"""Ograniczony odczyt metadanych IPv4 TCP SYN, bez zapisu payloadu."""

from datetime import datetime, timezone
import ipaddress
import os
import socket
import struct
import time


def parse_ipv4_syn(packet, *, now=None):
    if len(packet) < 40 or packet[0] >> 4 != 4 or packet[9] != 6:
        return None
    ip_header = (packet[0] & 15) * 4
    if ip_header < 20 or len(packet) < ip_header + 20:
        return None
    total = struct.unpack_from("!H", packet, 2)[0]
    if total < ip_header + 20 or total > len(packet):
        return None
    if struct.unpack_from("!H", packet, 6)[0] & 0x3FFF:
        return None
    tcp_header = (packet[ip_header + 12] >> 4) * 4
    if tcp_header < 20 or ip_header + tcp_header > total:
        return None
    flags = packet[ip_header + 13]
    if not flags & 2 or flags & 16:
        return None
    source = str(ipaddress.IPv4Address(packet[12:16]))
    destination = str(ipaddress.IPv4Address(packet[16:20]))
    source_port, destination_port, sequence = struct.unpack_from("!HHI", packet, ip_header)
    if not source_port or not destination_port:
        return None
    stamp = now or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise ValueError("Czas pakietu musi mieć strefę czasową.")
    return {"src": source, "dst": destination, "source_port": source_port,
            "port": destination_port, "protocol": "TCP", "syn": True,
            "syn_id": f"{source}:{source_port}>{destination}:{destination_port}/{sequence}",
            "timestamp": stamp.isoformat(), "epoch": stamp.timestamp()}


def capture_syn(local_ip, *, seconds=30, cancel_event=None, on_event=None,
                socket_factory=socket.socket, clock=time.monotonic, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Odczyt TCP SYN wymaga Windows.")
    address = ipaddress.IPv4Address(local_ip)
    if address.is_loopback or address.is_unspecified or address.is_multicast:
        raise ValueError("Wybierz lokalny IPv4 aktywnego adaptera.")
    if not 1 <= seconds <= 300:
        raise ValueError("Czas przechwytywania musi być w zakresie 1–300 s.")
    capture = socket_factory(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
    enabled = False
    count = 0
    try:
        capture.bind((str(address), 0))
        capture.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
        enabled = True
        capture.settimeout(0.5)
        deadline = clock() + seconds
        while clock() < deadline and not (cancel_event is not None and cancel_event.is_set()):
            try:
                packet = capture.recv(65535)
            except socket.timeout:
                continue
            event = parse_ipv4_syn(packet)
            if event is None or event["dst"] != str(address):
                continue
            count += 1
            if on_event is not None:
                on_event(event)
    finally:
        if enabled:
            try:
                capture.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
            except OSError:
                pass
        capture.close()
    return {"status": "CANCELLED" if cancel_event is not None and cancel_event.is_set() else "COMPLETE",
            "syn_events": count, "note": "Tylko metadane TCP SYN; payload nie jest zapisywany."}
