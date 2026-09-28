import sys

from PySide6.QtWidgets import QApplication

from prestige_core.ui_theme import install_font
from .gui import MonitorWindow


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    application = QApplication.instance() or QApplication(sys.argv)
    install_font(application)
    window = MonitorWindow()
    if "--smoke" in argv:
        assert window.table.columnCount() == 3
        window.close()
        return 0
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
