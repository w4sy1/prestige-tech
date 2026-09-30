import tempfile
import unittest
from pathlib import Path

from prestige_core.dns_history import DnsHistory


class DnsHistoryTests(unittest.TestCase):
    def test_opt_in_history_stores_summary_without_query_contents(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.sqlite"
            self.assertFalse(path.exists())
            history = DnsHistory(path)
            record = history.record({"ranking": [{"server": "1.1.1.1", "count": 3,
                                                  "successful": 2, "mean_ms": 14.5,
                                                  "error_rate": 1 / 3, "samples": [
                                                      {"secret_query": "do-not-save"}]}]})
            self.assertEqual(record["saved"], 1)
            self.assertEqual(history.recent()[0]["server"], "1.1.1.1")
            self.assertNotIn("do-not-save", str(history.recent()))
            with self.assertRaises(ValueError):
                history.record({"ranking": [{"server": "bad", "count": 3,
                                              "successful": 2, "error_rate": 0.3}]})
            self.assertEqual(len(history.recent()), 1)
            history.close()
            self.assertTrue(path.exists())

    def test_gui_history_stays_off_until_selected(self):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_network_center.gui import NetworkCenterWindow
        app = QApplication.instance() or QApplication([])
        window = NetworkCenterWindow(autoload=False)
        self.assertIsNone(window.dns_history)
        self.assertIn("wyłączona", window.dns_history_note.text())
        window.close()
