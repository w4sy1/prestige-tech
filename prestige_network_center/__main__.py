"""Uruchomienie GUI lub odczytu JSON z konsoli."""

import argparse
import json
import sys

from prestige_core.network import read_neighbors


def main(argv=None):
    parser = argparse.ArgumentParser(description="PRESTIGE TECH Network Center")
    parser.add_argument("--neighbors-json", action="store_true", help="odczytaj cache sąsiadów jako JSON")
    parser.add_argument("--smoke", action="store_true", help="sprawdź konstrukcję okna bez odczytu sieci")
    args = parser.parse_args(argv)
    if args.neighbors_json:
        print(json.dumps(read_neighbors(), ensure_ascii=False))
        return 0
    from PySide6.QtWidgets import QApplication
    from .gui import NetworkCenterWindow
    from prestige_core.ui_theme import install_font
    application = QApplication.instance() or QApplication(sys.argv)
    install_font(application)
    window = NetworkCenterWindow(autoload=not args.smoke)
    if args.smoke:
        assert window.table.columnCount() == 4
        window.close()
        return 0
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
