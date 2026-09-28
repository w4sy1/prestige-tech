"""GUI Android Center z odczytami ADB bez zmian telefonu."""

import json

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
                               QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget, QHeaderView)

from prestige_core.android_adb import AdbBackend, inspect_apps, list_devices, read_diagnostic
from prestige_core.ui_theme import APP_QSS, COLORS


class AndroidWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, action, *, serial=None, include_system=False, limit=200,
                 include_logcat=False, permission_package=None, parent=None):
        super().__init__(parent)
        self.action, self.serial = action, serial
        self.include_system, self.limit = include_system, limit
        self.include_logcat, self.permission_package = include_logcat, permission_package

    def run(self):
        try:
            backend = AdbBackend()
            if self.action == "devices":
                result = list_devices(backend)
            elif self.action == "diagnostic":
                packages = [self.permission_package] if self.permission_package else []
                result = read_diagnostic(self.serial, backend, include_logcat=self.include_logcat,
                                         package_permissions=packages)
            elif self.action == "apps":
                result = inspect_apps(self.serial, backend, include_system=self.include_system,
                                      limit=self.limit)
            else:
                raise ValueError("Nieprawidłowy odczyt Android Center.")
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class AndroidCenterWindow(QMainWindow):
    def __init__(self, *, autoload=True):
        super().__init__()
        self.setWindowTitle("PRESTIGE TECH — Android Center")
        self.resize(1040, 700)
        self.setMinimumSize(780, 550)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        self.devices = []
        self.apps = []
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(205)
        side = QVBoxLayout(sidebar)
        brand = QLabel("PRESTIGE TECH")
        brand.setStyleSheet(f"font-size: 16pt; font-weight: 700; color: {COLORS['info']};")
        side.addWidget(brand)
        side.addWidget(QLabel("ANDROID CENTER"))
        side.addStretch()
        side.addWidget(QLabel("By Dominik Wasilak"))
        layout.addWidget(sidebar)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 22, 24, 22)
        title = QLabel("Diagnostyka Androida")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        main.addWidget(title)
        main.addWidget(QLabel("Odczyt przez ADB. Telefon musi być odblokowany i autoryzowany."))
        controls = QHBoxLayout()
        self.refresh_button = QPushButton("Wykryj urządzenia")
        self.refresh_button.clicked.connect(self.refresh_devices)
        controls.addWidget(self.refresh_button)
        self.device_choice = QComboBox()
        controls.addWidget(self.device_choice, 1)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        controls.addWidget(self.help_button)
        main.addLayout(controls)
        self.status = QLabel("Nie odczytano urządzeń.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)

        tabs = QTabWidget()
        devices_card = QFrame()
        devices_card.setObjectName("Card")
        devices_layout = QVBoxLayout(devices_card)
        self.device_table = QTableWidget(0, 2)
        self.device_table.setHorizontalHeaderLabels(["Identyfikator", "Stan ADB"])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.setEditTriggers(QTableWidget.NoEditTriggers)
        devices_layout.addWidget(self.device_table)
        tabs.addTab(devices_card, "Urządzenia")

        diagnostic_card = QFrame()
        diagnostic_card.setObjectName("Card")
        diagnostic_layout = QVBoxLayout(diagnostic_card)
        self.diagnostic_button = QPushButton("Odczytaj diagnostykę")
        self.diagnostic_button.clicked.connect(self.start_diagnostic)
        diagnostic_layout.addWidget(self.diagnostic_button)
        diagnostic_options = QHBoxLayout()
        self.logcat_count = QCheckBox("Statystyki błędów logcat bez treści")
        diagnostic_options.addWidget(self.logcat_count)
        self.permission_package = QComboBox()
        self.permission_package.addItem("Bez szczegółów pakietu", None)
        diagnostic_options.addWidget(self.permission_package, 1)
        diagnostic_layout.addLayout(diagnostic_options)
        self.diagnostic_table = QTableWidget(0, 3)
        self.diagnostic_table.setHorizontalHeaderLabels(["Sekcja", "Stan", "Dane"])
        self.diagnostic_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.diagnostic_table.setEditTriggers(QTableWidget.NoEditTriggers)
        diagnostic_layout.addWidget(self.diagnostic_table)
        tabs.addTab(diagnostic_card, "ADB Diagnostic")

        apps_card = QFrame()
        apps_card.setObjectName("Card")
        apps_layout = QVBoxLayout(apps_card)
        app_controls = QHBoxLayout()
        self.include_system = QCheckBox("Uwzględnij systemowe")
        app_controls.addWidget(self.include_system)
        self.app_limit = QSpinBox()
        self.app_limit.setRange(1, 2000)
        self.app_limit.setValue(200)
        app_controls.addWidget(self.app_limit)
        self.apps_button = QPushButton("Odczytaj aplikacje")
        self.apps_button.clicked.connect(self.start_apps)
        app_controls.addWidget(self.apps_button)
        apps_layout.addLayout(app_controls)
        self.apps_table = QTableWidget(0, 4)
        self.apps_table.setHorizontalHeaderLabels(["Pakiet", "Wersja", "Ocena", "Deklaracje szczególne"])
        self.apps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.apps_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.apps_table.itemSelectionChanged.connect(self.show_selected_app)
        apps_layout.addWidget(self.apps_table, 2)
        self.app_details = QPlainTextEdit()
        self.app_details.setReadOnly(True)
        apps_layout.addWidget(self.app_details, 1)
        tabs.addTab(apps_card, "Android Inspector")
        main.addWidget(tabs, 1)
        layout.addWidget(content, 1)
        if autoload:
            self.refresh_devices()

    def _busy(self, value):
        for button in (self.refresh_button, self.diagnostic_button, self.apps_button):
            button.setEnabled(not value)

    def _start(self, action):
        if self.worker is not None and self.worker.isRunning():
            return
        serial = self.device_choice.currentData()
        if action != "devices" and serial is None:
            self.status.setText("Wybierz autoryzowane urządzenie z listy.")
            return
        self._busy(True)
        self.status.setText("Trwa odczyt ADB…")
        self.worker = AndroidWorker(action, serial=serial,
                                    include_system=self.include_system.isChecked(),
                                    limit=self.app_limit.value(),
                                    include_logcat=self.logcat_count.isChecked(),
                                    permission_package=self.permission_package.currentData(), parent=self)
        self.worker.loaded.connect(lambda result: self._show(action, result))
        self.worker.failed.connect(lambda message: self._error(action, message))
        self.worker.finished.connect(lambda: self._busy(False))
        self.worker.start()

    def refresh_devices(self):
        self._start("devices")

    def start_diagnostic(self):
        self._start("diagnostic")

    def start_apps(self):
        self._start("apps")

    def _show(self, action, result):
        if action == "devices":
            self.devices = result
            self.device_choice.clear()
            self.device_table.setRowCount(len(result))
            for index, row in enumerate(result):
                self.device_table.setItem(index, 0, QTableWidgetItem(row["serial"]))
                self.device_table.setItem(index, 1, QTableWidgetItem(row["state"]))
                if row["authorized"]:
                    self.device_choice.addItem(row["serial"], row["serial"])
            self.status.setText(f"Wykryto {len(result)} urządzeń; autoryzowane: "
                                f"{sum(row['authorized'] for row in result)}.")
        elif action == "diagnostic":
            rows = list(result["results"].items())
            self.diagnostic_table.setRowCount(len(rows))
            for index, (name, row) in enumerate(rows):
                value = row.get("data", "")
                if isinstance(value, dict):
                    value = json.dumps(value, ensure_ascii=False)
                for column, text in enumerate((name, row["status"], str(value)[:2000])):
                    self.diagnostic_table.setItem(index, column, QTableWidgetItem(text))
            self.status.setText(f"Diagnostyka: {result['status']}; {len(rows)} sekcji.")
        else:
            self.apps = result["apps"]
            self.permission_package.clear()
            self.permission_package.addItem("Bez szczegółów pakietu", None)
            self.apps_table.setRowCount(len(self.apps))
            for index, row in enumerate(self.apps):
                if row.get("status") is None:
                    self.permission_package.addItem(row["package"], row["package"])
                for column, value in enumerate((row["package"], row.get("version") or "",
                                                row.get("interest") or row.get("status") or "",
                                                ", ".join(row.get("special_indicators", [])))):
                    self.apps_table.setItem(index, column, QTableWidgetItem(value))
            self.status.setText(f"Aplikacje: {result['status']}; pokazano {len(self.apps)}; "
                                f"limit osiągnięty: {result['truncated']}.")

    def _error(self, action, message):
        if action == "devices":
            self.device_choice.clear()
            self.device_table.setRowCount(0)
        elif action == "diagnostic":
            self.diagnostic_table.setRowCount(0)
        else:
            self.apps = []
            self.apps_table.setRowCount(0)
            self.app_details.clear()
        self.status.setText(f"Odczyt niedostępny: {message}")

    def show_selected_app(self):
        index = self.apps_table.currentRow()
        if 0 <= index < len(self.apps):
            self.app_details.setPlainText(json.dumps(self.apps[index], ensure_ascii=False, indent=2))
        else:
            self.app_details.clear()

    def show_help(self):
        QMessageBox.information(self, "Pomoc Android Center",
                                "Włącz debugowanie USB i autoryzuj komputer na telefonie. "
                                "Wybierz urządzenie ze stanem device. Diagnostyka i lista aplikacji "
                                "są tylko odczytowe. Deklaracja uprawnienia nie oznacza aktywacji ani malware. "
                                "Brak dostępu do danych przez ADB jest pokazywany jako UNKNOWN/UNAVAILABLE.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(30000)
            if self.worker.isRunning():
                event.ignore()
                self.status.setText("Poczekaj na zakończenie odczytu ADB.")
                return
        super().closeEvent(event)
