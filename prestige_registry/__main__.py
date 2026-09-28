import sys

from PySide6.QtWidgets import QApplication

from prestige_core.ui_theme import install_font
from prestige_core.registry_read import OPERATIONS
from .gui import RegistryWindow


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    application = QApplication.instance() or QApplication(sys.argv)
    install_font(application)
    window = RegistryWindow()
    if "--smoke" in argv:
        assert window.operations.count() == len(OPERATIONS)
        window.close()
        return 0
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
