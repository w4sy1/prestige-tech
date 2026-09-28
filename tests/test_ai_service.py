import json
import os
from pathlib import Path
import tempfile
import unittest

from prestige_core.ai_service import external, local, preview


class AiServiceTests(unittest.TestCase):
    def test_local_report_normalizes_center_shapes_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "center.json"
            path.write_text(json.dumps({"sections": {
                "disk": {"status": "OK", "data": [{"Size": 1000, "FreeSpace": 40}]},
                "network": {"status": "OK", "data": [{"packet_loss_percent": 8}]},
                "security": {"status": "UNKNOWN", "data": []}}}), encoding="utf-8")
            result = local(path)
            self.assertEqual(result["metrics"]["disk_free_percent"], 4)
            self.assertEqual(result["metrics"]["packet_loss"], 8)
            self.assertFalse(result["data_leaves_device"])
            self.assertIn("LOW_DISK", {alert["code"] for alert in result["alerts"]})

    def test_preview_omits_source_alert_text_and_detects_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps({"packet_loss": 4, "alerts": [{
                "risk": "ŚREDNIE", "detected": "prywatna ścieżka użytkownika"}]}), encoding="utf-8")
            shown = preview(path, "gpt-5-mini")
            self.assertFalse(shown["data_leaves_device"])
            self.assertNotIn("prywatna ścieżka", shown["preview"]["input"])
            calls = []
            def analyzer(metrics, model):
                calls.append((metrics, model))
                return {"mode": "fixture"}
            self.assertEqual(external(path, "gpt-5-mini", expected_payload=shown["preview"],
                                      analyzer=analyzer)["mode"], "fixture")
            path.write_text(json.dumps({"packet_loss": 30}), encoding="utf-8")
            with self.assertRaises(ValueError):
                external(path, "gpt-5-mini", expected_payload=shown["preview"], analyzer=analyzer)
            self.assertEqual(len(calls), 1)


class AiGuiTests(unittest.TestCase):
    def test_external_disabled_until_preview(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_ai.gui import AiDialog
        app = QApplication.instance() or QApplication([])
        dialog = AiDialog()
        self.assertFalse(dialog.external_button.isEnabled())
        dialog.preview_payload = {"input": "{}"}
        dialog.set_buttons(True)
        self.assertTrue(dialog.external_button.isEnabled())
        dialog.source.setText("changed.json")
        self.assertFalse(dialog.external_button.isEnabled())
        dialog.close()
