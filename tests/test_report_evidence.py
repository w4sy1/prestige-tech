import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prestige_core.report_evidence import import_center_json
from prestige_core.security_rules import CHECK_NAMES


class ReportEvidenceTests(unittest.TestCase):
    def test_known_formats_and_private_values_stay_out_of_summary(self):
        cases = (
            ({"schema_version": 1, "source": "cache", "neighbors": [{"ips": ["192.168.1.5"],
               "hostname": "secret-host"}], "adapters": []}, "Network Center"),
            ({"schema_version": 1, "root": "C:/Private", "events": [{"at_utc": "2026-10-08T10:00:00Z",
               "path": "secret.txt", "kind": "Nowy"}]}, "Monitor Center"),
            ({"schema_version": 1, "serial": "PRIVATE-SERIAL", "apps": [{"package": "private.app"}]},
             "Android Center"),
            ({"schema_version": 1, "hive": "HKCU", "operation": "hide-fileext",
              "before": "secret", "applied": 0, "current": 0, "status": "PLAN"}, "Registry Manager"),
            ({"mode": "LOCAL MODE", "data_leaves_device": False, "alerts": [],
              "metrics": {"private": "secret"}}, "AI Center"),
            ({"mode": "EXTERNAL AI", "data_leaves_device": True,
              "sent_metrics": {"private": "secret"}, "analysis": "secret"}, "AI Center"),
            ({"coverage": {name: "UNKNOWN" if index < 2 else "EVALUATED"
                           for index, name in enumerate(CHECK_NAMES)},
              "risk_score": 8, "unknown_checks": 2,
              "alerts": [{"evidence": "secret"}]}, "Security Center"),
            ({"schema_version": 1, "files": [{"path": "private.txt", "sha256": "0" * 64}],
              "complete": False, "errors": ["secret"]}, "Storage & Recovery"),
            ({"status": "READY", "termux_detected": True,
              "commands": {"pkg": True}, "note": "secret"}, "Termux Center"),
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "result.json"
            for data, center in cases:
                source.write_text(json.dumps(data), encoding="utf-8")
                result = import_center_json(source)
                self.assertEqual(result["center"], center)
                self.assertEqual(len(result["sha256"]), 64)
                self.assertNotIn("secret", result["summary"].lower())
                self.assertNotIn("private", result["summary"].lower())

    def test_rejects_unknown_and_oversized_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "result.json"
            source.write_text('{"schema_version":1,"unrelated":true}', encoding="utf-8")
            with self.assertRaises(ValueError):
                import_center_json(source)
            source.write_bytes(b"x" * (16 * 1024 * 1024 + 1))
            with self.assertRaises(ValueError):
                import_center_json(source)

    def test_system_snapshot_counts_unknown_sections(self):
        from prestige_core.system_snapshot import QUERIES
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "snapshot.json"
            source.write_text(json.dumps({"schema_version": 1,
                "sections": {name: {"status": "UNKNOWN" if index == 0 else "OK", "data": []}
                             for index, name in enumerate(QUERIES)}}), encoding="utf-8")
            result = import_center_json(source)
            self.assertEqual(result["center"], "System Center")
            self.assertIn("1 UNKNOWN", result["summary"])

    def test_gui_import_keeps_diagnosis_and_final_test_empty(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMessageBox
        from prestige_report.gui import ReportDialog

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "result.json"
            source.write_text(json.dumps({"schema_version": 1, "root": "C:/Private",
                                          "events": []}), encoding="utf-8")
            dialog = ReportDialog()
            with patch("prestige_report.gui.QFileDialog.getOpenFileName",
                       return_value=(str(source), "")), patch.object(
                       QMessageBox, "question", return_value=QMessageBox.Yes):
                dialog.import_center_result()
            self.assertIn("Monitor Center", dialog.fields["wykonane_czynnosci"].toPlainText())
            self.assertEqual(dialog.fields["diagnoza"].toPlainText(), "")
            self.assertEqual(dialog.fields["test_koncowy"].toPlainText(), "")
            self.assertEqual(len(dialog.imported_sources), 1)
            dialog.close()

    def test_worker_rejects_changed_import_before_render(self):
        from prestige_report.gui import ReportWorker
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "result.json"
            source.write_text(json.dumps({"schema_version": 1, "root": "C:/Data",
                                          "events": []}), encoding="utf-8")
            evidence = import_center_json(source)
            source.write_text(json.dumps({"schema_version": 1, "root": "C:/Data",
                                          "events": [{"at_utc": "2026-10-08T10:00:00Z",
                                                      "path": "a", "kind": "Nowy"}]}), encoding="utf-8")
            failures = []
            worker = ReportWorker({}, directory, imported_sources=((str(source), evidence["sha256"]),))
            worker.failed.connect(failures.append)
            with patch("prestige_report.gui.render") as render:
                worker.run()
                render.assert_not_called()
            self.assertIn("zmienił", failures[0])


if __name__ == "__main__":
    unittest.main()
