import os
import unittest
from unittest.mock import patch


class RegistryGuiTests(unittest.TestCase):
    def test_result_then_error_removes_stale_values(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_core.registry_read import OPERATIONS
        from prestige_registry.gui import RegistryWindow
        application = QApplication.instance() or QApplication([])
        window = RegistryWindow()
        self.assertEqual(window.operations.count(), len(OPERATIONS))
        window.search.setText("Jednorazowy")
        self.assertEqual(window.operations.count(), 2)
        window.search.clear()
        window.operations.setCurrentRow(0)
        self.assertTrue(window.read_button.isEnabled())
        window.show_result({
            "status": "OK", "reason": None,
            "rows": [{"name": "Desktop", "value": r"%USERPROFILE%\Desktop", "type": 2, "status": "OK"}],
        })
        self.assertEqual(window.table.rowCount(), 1)
        window.show_error("Odmowa dostępu")
        self.assertEqual(window.table.rowCount(), 0)
        self.assertIn("Odmowa", window.status.text())
        with patch("prestige_registry.gui.load_admx_catalog") as loader:
            from prestige_core.registry_read import ReadOperation
            loader.return_value = {"status": "COMPLETE", "templates": 1, "errors": [],
                                   "operations": (ReadOperation("REG-ADMX-0001", "Fixture", "Zasady ADMX",
                                                                "Odczyt", "HKCU", "Software\\Fixture",
                                                                ("Flag",), "fixture.admx"),)}
            window.load_admx()
            self.assertEqual(window.operations.count(), len(OPERATIONS) + 1)
            window.search.setText("Fixture")
            self.assertEqual(window.operations.count(), 1)
        window.close()


if __name__ == "__main__":
    unittest.main()
