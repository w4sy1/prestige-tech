import sys

from PySide6.QtWidgets import QApplication
from prestige_core.ui_theme import install_font

from .gui import SystemCenterWindow


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    install_font(app)
    window = SystemCenterWindow()
    if "--smoke" in sys.argv:
        window.close()
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
