"""Launcher źródłowego GUI Termux Center."""

import os
import sys

from PySide6.QtWidgets import QApplication
from prestige_core.ui_theme import install_font

from prestige_termux.gui import TermuxCenterWindow


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    install_font(app)
    window = TermuxCenterWindow()
    window.show()
    if "--smoke" in sys.argv:
        app.processEvents()
        window.close()
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
