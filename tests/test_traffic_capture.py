from datetime import datetime, timezone
import socket
import struct
from threading import Event
import unittest

from prestige_core.traffic_capture import capture_syn, parse_ipv4_syn


def packet(*, flags=2, destination="192.0.2.3"):
    ip = bytearray(40)
    ip[0] = 0x45
    ip[9] = 6
    struct.pack_into("!H", ip, 2, 40)
    ip[12:16] = bytes((192, 0, 2, 2))
    ip[16:20] = socket.inet_aton(destination)
    struct.pack_into("!HHI", ip, 20, 12345, 22, 42)
    ip[32] = 0x50
    ip[33] = flags
    return bytes(ip)


class FakeSocket:
    def __init__(self):
        self.calls = []
        self.sent = False

    def bind(self, address):
        self.calls.append(("bind", address))

    def ioctl(self, code, value):
        self.calls.append(("ioctl", value))

    def settimeout(self, value):
        self.calls.append(("timeout", value))

    def recv(self, size):
        if not self.sent:
            self.sent = True
            return packet()
        raise socket.timeout()

    def close(self):
        self.calls.append(("close", None))


class TrafficCaptureTest(unittest.TestCase):
    def test_parser_accepts_syn_only(self):
        row = parse_ipv4_syn(packet(), now=datetime(2026, 9, 27, tzinfo=timezone.utc))
        self.assertEqual(row["port"], 22)
        self.assertEqual(row["src"], "192.0.2.2")
        self.assertIsNone(parse_ipv4_syn(packet(flags=18)))
        self.assertIsNone(parse_ipv4_syn(packet()[:20]))

    def test_capture_filters_target_and_disables_raw_socket(self):
        fake = FakeSocket()
        cancel = Event()
        def on_event(row):
            self.assertEqual(row["dst"], "192.0.2.3")
            cancel.set()
        result = capture_syn("192.0.2.3", seconds=5, cancel_event=cancel,
                             on_event=on_event, socket_factory=lambda *args: fake,
                             clock=lambda: 0, platform="nt")
        self.assertEqual(result["syn_events"], 1)
        self.assertEqual(result["status"], "CANCELLED")
        self.assertEqual(fake.calls[-1], ("close", None))
        self.assertEqual(fake.calls[-2][1], socket.RCVALL_OFF)

    def test_bad_address_rejected_before_opening_socket(self):
        with self.assertRaises(ValueError):
            capture_syn("127.0.0.1", socket_factory=lambda *args: self.fail("opened"), platform="nt")
