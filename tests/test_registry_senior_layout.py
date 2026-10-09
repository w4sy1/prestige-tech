import os
import unittest


class RegistrySeniorLayoutTests(unittest.TestCase):
    def test_minimum_window_keeps_results_reachable_without_horizontal_scroll(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_registry.gui import RegistryWindow

        app = QApplication.instance() or QApplication([])
        window = RegistryWindow()
        window.resize(820, 560)
        window.show()
        app.processEvents()
        try:
            self.assertGreaterEqual(window.table.height(), 170)
            self.assertGreaterEqual(window.operations.height(), 100)
            self.assertGreater(window.content_scroll.verticalScrollBar().maximum(), 0)
            self.assertEqual(window.content_scroll.horizontalScrollBar().maximum(), 0)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
