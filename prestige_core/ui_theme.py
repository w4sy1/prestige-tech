"""Tokeny nowych Centrów; Dashboard zachowuje własny, gotowy wygląd."""

from pathlib import Path
import sys


def install_font(application):
    """Użyj załączonej czcionki także w uruchomionym EXE."""
    from PySide6.QtGui import QFont, QFontDatabase

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    path = base / "DejaVuSans.ttf" if getattr(sys, "frozen", False) else base / "assets" / "DejaVuSans.ttf"
    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id < 0:
        raise RuntimeError("Brak czcionki interfejsu DejaVu Sans.")
    family = QFontDatabase.applicationFontFamilies(font_id)[0]
    application.setFont(QFont(family, 10))

COLORS = {
    "background": "#020812", "surface": "#071827", "surface_alt": "#092138",
    "border": "#154767", "primary": "#078cff", "primary_hover": "#103653",
    "success": "#45d99a", "warning": "#ffd04a", "danger": "#ef5b65",
    "info": "#28c8ff", "text_primary": "#f4f8fc",
    "text_secondary": "#a2b5c7", "text_muted": "#7890a5",
}


def center_header(title, subtitle):
    """Spójny nagłówek narzędzi źródłowych bez zależności od Dashboardu."""
    from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

    header = QFrame()
    header.setObjectName("Card")
    layout = QVBoxLayout(header)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(4)
    brand = QLabel("PRESTIGE TECH")
    brand.setStyleSheet(f"color: {COLORS['info']}; font-size: 10pt; font-weight: 700;")
    layout.addWidget(brand)
    heading = QLabel(title)
    heading.setStyleSheet("font-size: 18pt; font-weight: 700;")
    layout.addWidget(heading)
    description = QLabel(subtitle)
    description.setWordWrap(True)
    description.setStyleSheet(f"color: {COLORS['text_secondary']};")
    layout.addWidget(description)
    return header

APP_QSS = """
QWidget { background: #020812; color: #f4f8fc; font-family: 'DejaVu Sans'; font-size: 10pt; }
QLabel, QCheckBox, QRadioButton { background: transparent; }
QCheckBox::indicator { width: 15px; height: 15px; background: #071827;
                       border: 1px solid #54758f; border-radius: 4px; }
QCheckBox::indicator:checked { background: #078cff; border-color: #28c8ff; }
QCheckBox::indicator:disabled { background: #071827; border-color: #12344c; }
QFrame#Sidebar { background: #061321; border-right: 1px solid #154767; }
QFrame#Sidebar QLabel { background: transparent; }
QFrame#Card { background: #092138; border: 1px solid #154767; border-radius: 12px; }
QFrame#Card QLabel { background: transparent; }
QPushButton { background: #0b2237; color: #f4f8fc; border: 1px solid #154767;
              border-radius: 8px; padding: 8px 12px; min-height: 22px; text-align: left; }
QPushButton:hover { background: #103653; border-color: #078cff; }
QPushButton:pressed { background: #078cff; color: #ffffff; }
QPushButton:disabled { color: #7890a5; background: #071827; border-color: #12344c; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus, QTableWidget:focus {
    border: 1px solid #28c8ff;
}
QLineEdit, QComboBox, QSpinBox, QDateEdit, QPlainTextEdit, QTextEdit,
QListWidget, QTreeWidget {
    background: #071827; color: #f4f8fc; selection-background-color: #103653;
    border: 1px solid #154767; border-radius: 8px; padding: 6px;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { color: #7890a5; }
QComboBox::drop-down { border: none; width: 22px; }
QTableWidget { background: #071827; alternate-background-color: #092138;
               selection-background-color: #103653; gridline-color: #154767;
               border: 1px solid #154767; border-radius: 8px; }
QHeaderView::section { background: #092138; color: #f4f8fc; border: 1px solid #154767;
                       padding: 6px; }
QTabWidget::pane { border: 1px solid #154767; border-radius: 8px; background: #071827; }
QTabBar::tab { background: #092138; color: #a2b5c7; border: 1px solid #154767;
               border-top-left-radius: 8px; border-top-right-radius: 8px;
               padding: 8px 14px; }
QTabBar::tab:hover { color: #f4f8fc; background: #103653; }
QTabBar::tab:selected { color: #28c8ff; border-bottom: 2px solid #28c8ff; }
QScrollBar:vertical { background: #071827; width: 11px; margin: 0; }
QScrollBar::handle:vertical { background: #154767; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #078cff; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #071827; height: 11px; margin: 0; }
QScrollBar::handle:horizontal { background: #154767; border-radius: 5px; min-width: 24px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QProgressBar { background: #071827; border: 1px solid #154767; border-radius: 6px;
               text-align: center; color: #f4f8fc; }
QProgressBar::chunk { background: #078cff; border-radius: 5px; }
QToolTip { background: #092138; color: #f4f8fc; border: 1px solid #28c8ff; padding: 6px; }
"""
