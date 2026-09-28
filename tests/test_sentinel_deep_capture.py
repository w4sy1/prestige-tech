import io
import threading
import unittest
from unittest.mock import Mock

from prestige_core.sentinel_deep_capture import DeepDetector, capture, list_interfaces, parse_line


def row(epoch, source="192.0.2.10", destination="192.0.2.20", *, port="80", syn="1"):
    return "|".join((str(epoch), "", source, destination, "12345", port, syn, "0",
                     "", "", "", "", "")) + "\n"


class DeepCaptureTests(unittest.TestCase):
    def test_parser_and_tcp_threshold(self):
        event = parse_line(row(1))
        self.assertEqual(event["protocol"], "TCP")
        detector = DeepDetector(local_ips=["192.0.2.20"])
        alerts = []
        for port in range(1, 31):
            alert = detector.process(parse_line(row(port, port=str(port))))
            if alert:
                alerts.append(alert)
        self.assertEqual([alert["severity"] for alert in alerts], ["MEDIUM", "HIGH"])

    def test_arp_sweep_and_bad_rows(self):
        detector = DeepDetector()
        alerts = []
        for target in range(1, 19):
            parts = ["1", "aa:bb:cc:dd:ee:ff", "", "", "", "", "", "", "", "", "",
                     "192.0.2.8", f"192.0.2.{target}"]
            alert = detector.process(parse_line("|".join(parts)))
            if alert:
                alerts.append(alert)
        self.assertEqual(alerts[0]["category"], "ARP sweep")
        with self.assertRaises(ValueError):
            parse_line("wrong")

    def test_interface_list(self):
        runner = Mock(return_value=Mock(returncode=0, stdout="1. \\Device\\NPF_A (Ethernet)\n"))
        self.assertEqual(list_interfaces(executable="tshark", runner=runner)[0]["index"], 1)

    def test_capture_early_exit_is_unknown(self):
        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(row(1))

            def poll(self):
                return 0

            def wait(self, timeout=None):
                return 0

        result = capture(1, seconds=1, executable="tshark", launcher=lambda *a, **k: FakeProcess(),
                         platform="nt")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["packets"], 1)

    def test_cancelled_capture(self):
        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO("")

            def poll(self):
                return 0

            def wait(self, timeout=None):
                return 0

        flag = threading.Event()
        flag.set()
        result = capture(1, seconds=1, executable="tshark", launcher=lambda *a, **k: FakeProcess(),
                         platform="nt", cancel_event=flag)
        self.assertEqual(result["status"], "CANCELLED")


if __name__ == "__main__":
    unittest.main()
