"""GUI pierwszej funkcji Security Center: inspekcja pliku bez wykonania."""

import json

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QSpinBox,
                               QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
                               QVBoxLayout, QWidget)

from prestige_core.file_inspector import inspect_file
from prestige_core.security_check import audit_windows, load_evidence
from prestige_core.security_rules import audit
from prestige_core.malware_triage import triage_windows
from prestige_core.malware_rules import analyze
from prestige_core.ui_theme import APP_QSS, COLORS
from prestige_report.gui import ReportDialog
from prestige_core.report_prefill import summarize_center_result
from prestige_ai.gui import AiDialog


class SecurityWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, action, path=None, include_strings=False, seconds=30, parent=None):
        super().__init__(parent)
        self.action = action
        self.path = path
        self.include_strings = include_strings
        self.seconds = seconds

    def run(self):
        try:
            if self.action == "file":
                result = inspect_file(self.path, include_strings=self.include_strings)
            elif self.action == "audit":
                result = audit_windows()
            elif self.action == "offline":
                result = audit(load_evidence(self.path))
            elif self.action == "triage":
                result = triage_windows(self.seconds)
            elif self.action == "triage_folder":
                result = triage_windows(self.seconds, scan_paths=(self.path,))
            elif self.action == "triage_offline":
                result = analyze(load_evidence(self.path))
            else:
                raise ValueError("Nieznana operacja Security Center.")
            self.loaded.emit({"action": self.action, "data": result})
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class SecurityCenterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRESTIGE TECH — Security Center")
        self.resize(900, 650)
        self.setMinimumSize(700, 500)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        self.report_dialog = None
        self.report_prefill = None
        self.ai_dialog = None
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(24, 22, 24, 22)
        brand = QLabel("PRESTIGE TECH")
        brand.setStyleSheet(f"font-size: 16pt; font-weight: 700; color: {COLORS['info']};")
        main.addWidget(brand)
        title = QLabel("Security Center")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        main.addWidget(title)
        main.addWidget(QLabel("Odczyt pliku, konfiguracji Windows i heurystyka procesów bez zmian systemu."))
        controls = QHBoxLayout()
        self.choose_button = QPushButton("Wybierz plik i analizuj")
        self.choose_button.clicked.connect(self.choose_file)
        controls.addWidget(self.choose_button)
        self.strings_checkbox = QCheckBox("Dołącz ciągi znaków (mogą zawierać prywatne dane)")
        controls.addWidget(self.strings_checkbox)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        controls.addWidget(self.help_button)
        self.report_button = QPushButton("Raport serwisowy")
        self.report_button.clicked.connect(self.open_report)
        controls.addWidget(self.report_button)
        main.addLayout(controls)
        audit_controls = QHBoxLayout()
        self.audit_button = QPushButton("Audyt konfiguracji Windows")
        self.audit_button.clicked.connect(self.start_audit)
        audit_controls.addWidget(self.audit_button)
        self.offline_button = QPushButton("Analizuj zapisany JSON Security Check")
        self.offline_button.clicked.connect(self.choose_offline_audit)
        audit_controls.addWidget(self.offline_button)
        self.ai_button = QPushButton("Analiza AI")
        self.ai_button.clicked.connect(self.open_ai)
        audit_controls.addWidget(self.ai_button)
        main.addLayout(audit_controls)
        triage_controls = QHBoxLayout()
        self.triage_seconds = QSpinBox()
        self.triage_seconds.setRange(1, 300)
        self.triage_seconds.setValue(30)
        self.triage_seconds.setSuffix(" s próbki")
        triage_controls.addWidget(self.triage_seconds)
        self.triage_button = QPushButton("Malware Triage")
        self.triage_button.clicked.connect(self.start_triage)
        triage_controls.addWidget(self.triage_button)
        self.triage_folder_button = QPushButton("Triage + wybrany folder")
        self.triage_folder_button.clicked.connect(self.choose_triage_folder)
        triage_controls.addWidget(self.triage_folder_button)
        self.triage_offline_button = QPushButton("Triage z JSON")
        self.triage_offline_button.clicked.connect(self.choose_triage_offline)
        triage_controls.addWidget(self.triage_offline_button)
        main.addLayout(triage_controls)
        self.raw_evidence = QCheckBox("Pokaż surowe dane Triage (alerty i korelacje również mogą zawierać prywatne ścieżki)")
        main.addWidget(self.raw_evidence)
        self.status = QLabel("Wybierz plik do odczytu.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        card_layout.addWidget(self.result)
        main.addWidget(card, 1)

    def choose_file(self):
        if self.worker is not None and self.worker.isRunning():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Plik do analizy")
        if path:
            self.inspect(path)

    def inspect(self, path):
        self._start("file", path)

    def start_audit(self):
        self._start("audit")

    def choose_offline_audit(self):
        path, _ = QFileDialog.getOpenFileName(self, "JSON odczytów Security Check", "", "JSON (*.json)")
        if path:
            self._start("offline", path)

    def start_triage(self):
        self._start("triage")

    def choose_triage_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Folder do odczytowego skanu plików")
        if path:
            self._start("triage_folder", path)

    def choose_triage_offline(self):
        path, _ = QFileDialog.getOpenFileName(self, "JSON dowodów Malware Triage", "", "JSON (*.json)")
        if path:
            self._start("triage_offline", path)

    def _start(self, action, path=None):
        if self.worker is not None and self.worker.isRunning():
            return
        self.choose_button.setEnabled(False)
        self.audit_button.setEnabled(False)
        self.offline_button.setEnabled(False)
        self.triage_button.setEnabled(False)
        self.triage_folder_button.setEnabled(False)
        self.triage_offline_button.setEnabled(False)
        self.status.setText("Trwa odczyt…")
        self.worker = SecurityWorker(action, path, self.strings_checkbox.isChecked(),
                                     self.triage_seconds.value(), self)
        self.worker.loaded.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def _finished(self):
        self.choose_button.setEnabled(True)
        self.audit_button.setEnabled(True)
        self.offline_button.setEnabled(True)
        self.triage_button.setEnabled(True)
        self.triage_folder_button.setEnabled(True)
        self.triage_offline_button.setEnabled(True)

    def show_result(self, result):
        try:
            self.report_prefill = summarize_center_result("Security", result["action"], result)
        except (ValueError, KeyError, TypeError):
            self.report_prefill = None
        data = result["data"]
        if result["action"] == "file":
            self.status.setText(f"Analiza zakończona: {data['name']}")
        elif result["action"] in ("audit", "offline"):
            self.status.setText(f"Audyt zakończony: {data['unknown_checks']} kontroli UNKNOWN, wynik {data['risk_score']}/100.")
        else:
            self.status.setText(f"Triage zakończony: {len(data['alerts'])} alertów, "
                                f"{len(data['unknown_sections'])} sekcji UNKNOWN. Alert nie jest werdyktem malware.")
            if not self.raw_evidence.isChecked():
                data = {key: value for key, value in data.items() if key != "evidence"}
        self.result.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))

    def show_error(self, message):
        self.report_prefill = None
        self.status.setText("Nie ukończono analizy.")
        self.result.setPlainText(message)

    def show_help(self):
        QMessageBox.information(self, "Pomoc — Security Center",
                                "Inspekcja odczytuje plik bez uruchamiania. SHA-256/SHA-512 identyfikują treść; "
                                "SHA-1/MD5 są tylko dla zgodności. Entropia i brak podpisu nie dowodzą złośliwości. "
                                "Ciągi znaków mogą zawierać dane prywatne i są domyślnie wyłączone. "
                                "Stan podpisu Authenticode wymaga Windows; nieznany stan nie oznacza poprawnego podpisu. "
                                "Audyt Windows obejmuje 21 kategorii i zgłasza UNKNOWN przy braku danych. Wynik nie jest "
                                "prawdopodobieństwem infekcji. Malware Triage próbkuje CPU/GPU i koreluje procesy z "
                                "autostartem oraz połączeniami. Jego alerty wymagają ręcznej oceny. Skan folderu nie "
                                "uruchamia znalezionych plików. Offline JSON wymaga danych kontroli, nie końcowego raportu.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Poczekaj na zakończenie odczytu przed zamknięciem.")
            event.ignore()
            return
        super().closeEvent(event)

    def open_report(self):
        self.report_dialog = ReportDialog(self, prefill=self.report_prefill)
        self.report_dialog.show()

    def open_ai(self):
        self.ai_dialog = AiDialog(self)
        self.ai_dialog.show()
