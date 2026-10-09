import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prestige_core.report_evidence import import_center_json
from prestige_core.security_rules import audit


class SecurityAuditExportTest(unittest.TestCase):
    def test_saved_audit_can_be_imported_into_report(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_security.gui import SecurityCenterWindow

        app = QApplication.instance() or QApplication([])
        window = SecurityCenterWindow()
        result = audit({})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            window.show_result({"action": "audit", "data": result})
            with patch("prestige_security.gui.QFileDialog.getSaveFileName",
                       return_value=(str(path), "")):
                window.export_audit()
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), result)
            imported = import_center_json(path)
            self.assertEqual(imported["center"], "Security Center")
        window.close()


if __name__ == "__main__":
    unittest.main()
