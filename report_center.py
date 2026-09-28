"""Samodzielne wejście do wspólnego Repair Report."""

import sys

from PySide6.QtWidgets import QApplication
from prestige_core.ui_theme import install_font

from prestige_report.gui import ReportDialog


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    install_font(app)
    dialog = ReportDialog()
    dialog.show()
    if "--smoke" in sys.argv:
        app.processEvents()
        dialog.close()
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
