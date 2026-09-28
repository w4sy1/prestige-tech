"""Wspólne źródłowe GUI Termux Setup i Toolkit."""

import json
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
                               QPushButton, QVBoxLayout, QWidget)

from prestige_core import termux_setup, termux_toolkit
from prestige_core.ui_theme import APP_QSS, center_header


class TermuxWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, area, options, parent=None):
        super().__init__(parent)
        self.area, self.options = area, options

    def run(self):
        try:
            args = SimpleNamespace(**self.options)
            result = (termux_setup.handle(args) if self.area == "setup"
                      else termux_toolkit.handle(args))
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
            self.failed.emit(str(error))


class TermuxCenterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRESTIGE TECH — Termux Center")
        self.resize(850, 650)
        self.setMinimumSize(650, 500)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.addWidget(center_header("Termux Center", "Setup: plan i cofnięcie konfiguracji. Toolkit: osiem kategorii operacji."))
        form = QFormLayout()
        self.area = QComboBox()
        self.area.addItems(("Setup", "Toolkit"))
        self.area.currentTextChanged.connect(self.update_fields)
        form.addRow("Obszar", self.area)
        self.profile = QComboBox()
        self.profile.addItems(termux_setup.PROFILES)
        form.addRow("Profil pakietów", self.profile)
        self.category = QComboBox()
        self.category.addItems(termux_toolkit.CATEGORIES)
        self.category.currentTextChanged.connect(self.update_operations)
        form.addRow("Kategoria", self.category)
        self.operation = QComboBox()
        form.addRow("Operacja", self.operation)
        self.root = QLineEdit(str(Path.home()))
        form.addRow("Katalog źródłowy / Git", self.root)
        self.target = QLineEdit()
        form.addRow("Cel ping IPv4/IPv6", self.target)
        self.file = QLineEdit()
        form.addRow("Plik do SHA-256", self.file)
        self.archive = QLineEdit()
        form.addRow("Nowe archiwum / weryfikacja", self.archive)
        self.rollback = QLineEdit()
        form.addRow("Katalog kopii Setup do cofnięcia", self.rollback)
        self.git_name = QLineEdit()
        form.addRow("Git: nazwa (opcjonalnie)", self.git_name)
        self.git_email = QLineEdit()
        form.addRow("Git: e-mail (opcjonalnie)", self.git_email)
        self.ssh = QCheckBox("Konfiguruj klienta SSH")
        form.addRow("", self.ssh)
        self.apply = QCheckBox("Zezwól na zmianę Setup / utworzenie archiwum")
        form.addRow("", self.apply)
        layout.addLayout(form)
        controls = QHBoxLayout()
        self.run_button = QPushButton("Uruchom / pokaż plan")
        self.run_button.clicked.connect(self.start)
        controls.addWidget(self.run_button)
        self.file_button = QPushButton("Wybierz plik")
        self.file_button.clicked.connect(self.choose_file)
        controls.addWidget(self.file_button)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        controls.addWidget(self.help_button)
        layout.addLayout(controls)
        self.status = QLabel("Wybierz operację.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        layout.addWidget(self.result, 1)
        self.update_operations()
        self.update_fields()

    def update_operations(self):
        self.operation.clear()
        self.operation.addItems(termux_toolkit.OPERATIONS[self.category.currentText()])

    def update_fields(self):
        setup = self.area.currentText() == "Setup"
        for widget in (self.profile, self.rollback, self.git_name, self.git_email, self.ssh):
            widget.setEnabled(setup)
        for widget in (self.category, self.operation, self.root, self.target, self.file,
                       self.archive, self.file_button):
            widget.setEnabled(not setup)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Plik do obliczenia SHA-256")
        if path:
            self.file.setText(path)

    def start(self):
        if self.worker is not None and self.worker.isRunning():
            return
        area = "setup" if self.area.currentText() == "Setup" else "toolkit"
        apply = self.apply.isChecked()
        if apply:
            confirmation = QMessageBox.question(
                self, "Potwierdź wykonanie", "Wykonać wybraną operację Termux?\n"
                "Setup zmienia konfigurację i może instalować pakiety; Backup tworzy archiwum.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if confirmation != QMessageBox.Yes:
                return
        if area == "setup":
            options = dict(profile=self.profile.currentText(), apply=apply,
                           rollback=self.rollback.text().strip() or None,
                           git_name=self.git_name.text().strip() or None,
                           git_email=self.git_email.text().strip() or None,
                           ssh_client=self.ssh.isChecked())
        else:
            options = dict(menu=False, category=self.category.currentText(),
                           operation=self.operation.currentText(), root=self.root.text().strip(),
                           target=self.target.text().strip() or None,
                           file=self.file.text().strip() or None,
                           archive=self.archive.text().strip() or None, apply=apply)
        self.run_button.setEnabled(False)
        self.status.setText("Trwa operacja…")
        self.worker = TermuxWorker(area, options, self)
        self.worker.loaded.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(lambda: self.run_button.setEnabled(True))
        self.worker.start()

    def show_result(self, value):
        self.status.setText("Plan gotowy." if value.get("dry_run") or value.get("plan") else "Operacja zakończona.")
        self.result.setPlainText(json.dumps(value, ensure_ascii=False, indent=2, default=str))

    def show_error(self, message):
        self.status.setText("Nie ukończono operacji.")
        self.result.setPlainText(message)

    def show_help(self):
        QMessageBox.information(self, "Pomoc — Termux Center",
                                "Setup bez wykonania pokazuje plan. Odczytowe operacje Toolkit uruchamiają się po kliknięciu. "
                                "Wykonanie Setup wymaga Termuxa z pkg; "
                                "przed zmianą plików zapisuje kopię i odmawia cofnięcia, jeśli plik później zmieniono. "
                                "Toolkit korzysta z poleceń systemowych. Backup wyklucza znane sekrety i tworzy "
                                "archiwum poza źródłem; weryfikacja porównuje SHA-256 z manifestem. "
                                "Nie wpisuj prywatnego klucza SSH w formularz.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Poczekaj na zakończenie operacji przed zamknięciem.")
            event.ignore()
            return
        super().closeEvent(event)
