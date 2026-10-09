import unittest

from prestige_core.monitor_timeline import compare_periods, filter_events


class MonitorTimelineTest(unittest.TestCase):
    def test_filters_by_kind_path_and_utc_period_without_mutation(self):
        rows = [
            {"at_utc": "2026-10-01T10:00:00Z", "path": "a.txt", "kind": "Nowy"},
            {"at_utc": "2026-10-02T10:00:00+00:00", "path": "b.txt", "kind": "Zmieniony"},
        ]
        selected = filter_events(rows, path="B.TXT", kind="Zmieniony",
                                 start="2026-10-02T00:00:00Z", end="2026-10-03T00:00:00Z")
        self.assertEqual(selected, [rows[1]])
        self.assertEqual(len(rows), 2)

    def test_invalid_period_is_rejected(self):
        with self.assertRaises(ValueError):
            filter_events([], start="2026-10-03T00:00:00Z", end="2026-10-02T00:00:00Z")
        with self.assertRaises(ValueError):
            filter_events([], start="2026-10-02T00:00:00")

    def test_compare_two_periods_uses_saved_events_only(self):
        rows = [
            {"at_utc": "2026-10-01T10:00:00Z", "path": "a.txt", "kind": "Nowy"},
            {"at_utc": "2026-10-03T10:00:00Z", "path": "b.txt", "kind": "Usunięty"},
        ]
        result = compare_periods(rows, "2026-10-01T00:00:00Z", "2026-10-02T00:00:00Z",
                                 "2026-10-03T00:00:00Z", "2026-10-04T00:00:00Z")
        self.assertEqual(result["first"]["by_kind"], {"Nowy": 1})
        self.assertEqual(result["second"]["by_kind"], {"Usunięty": 1})
        with self.assertRaises(ValueError):
            compare_periods(rows, "2026-10-01T00:00:00Z", "2026-10-03T00:00:00Z",
                            "2026-10-02T00:00:00Z", "2026-10-04T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
