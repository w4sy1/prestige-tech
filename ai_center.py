"""Samodzielne wejście do wspólnego AI Diagnostic Assistant."""

import sys

from PySide6.QtWidgets import QApplication
from prestige_core.ui_theme import install_font

from prestige_ai.gui import AiDialog


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    install_font(app)
    dialog = AiDialog()
    dialog.show()
    if "--smoke" in sys.argv:
        app.processEvents()
        dialog.close()
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
