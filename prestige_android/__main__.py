"""Launcher Android Center."""

import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="PRESTIGE TECH Android Center")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    from PySide6.QtWidgets import QApplication
    from prestige_core.ui_theme import install_font
    from .gui import AndroidCenterWindow
    app = QApplication.instance() or QApplication(sys.argv)
    install_font(app)
    window = AndroidCenterWindow(autoload=not args.smoke)
    if args.smoke:
        assert window.device_table.columnCount() == 2
        window.close()
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
