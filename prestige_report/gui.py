"""Wielokrotnego użytku formularz Repair Report dla Centrów."""

from datetime import date
from pathlib import Path
import uuid

from PySide6.QtCore import QDate, QThread, Signal
from PySide6.QtWidgets import (QDateEdit, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
                               QSpinBox, QTextEdit, QVBoxLayout, QWidget)

from prestige_core.pdf_export import export_pdf
from prestige_core.report_service import LABELS, render, template, validate
from prestige_core.ui_theme import APP_QSS, center_header


LONG_FIELDS = frozenset(("zgloszony_problem", "diagnoza", "wykonane_czynnosci",
                         "zalecenia", "test_koncowy", "czesci"))


class ReportWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, record, directory, parent=None):
        super().__init__(parent)
        self.record, self.directory = record, directory

    def run(self):
        try:
            result = render(self.record, self.directory)
            pdf_path = str(Path(result["files"][0]).with_suffix(".pdf"))
            try:
                export_pdf({LABELS[key]: value for key, value in self.record.items()},
                           pdf_path, "Raport serwisowy")
            except (OSError, ValueError, RuntimeError, ImportError) as error:
                result["pdf_error"] = str(error)
            else:
                result["files"].append(pdf_path)
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError, TypeError) as error:
            self.failed.emit(str(error))


class ReportDialog(QDialog):
    def __init__(self, parent=None, *, prefill=None):
        super().__init__(parent)
        self.setWindowTitle("PRESTIGE TECH — Repair Report")
        self.resize(780, 700)
        self.setMinimumSize(620, 500)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        self.fields = {}
        main = QVBoxLayout(self)
        main.addWidget(center_header("Repair Report", "Raport serwisowy — dane pozostają lokalne."))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QFormLayout(body)
        defaults = template()
        defaults["numer_zlecenia"] = "PT-" + date.today().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
        for name, label in LABELS.items():
            if name == "data":
                widget = QDateEdit(QDate.currentDate())
                widget.setCalendarPopup(True)
            elif name == "czas_pracy_min":
                widget = QSpinBox()
                widget.setRange(0, 100000)
                widget.setSuffix(" min")
            elif name in LONG_FIELDS:
                widget = QTextEdit()
                widget.setFixedHeight(82)
                if isinstance(defaults[name], str):
                    widget.setPlainText(defaults[name])
            else:
                widget = QLineEdit(str(defaults[name]))
            form.addRow(label, widget)
            self.fields[name] = widget
        scroll.setWidget(body)
        main.addWidget(scroll, 1)
        actions = QHBoxLayout()
        self.generate_button = QPushButton("Zapisz HTML / JSON / TXT / PDF")
        self.generate_button.clicked.connect(self.generate)
        actions.addWidget(self.generate_button)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        actions.addWidget(self.help_button)
        main.addLayout(actions)
        self.status = QLabel("Wypełnij wymagane pola i wybierz katalog docelowy.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        if prefill:
            for name in ("diagnoza", "wykonane_czynnosci"):
                value = prefill.get(name)
                if isinstance(value, str):
                    self.fields[name].setPlainText(value)
            self.status.setText("Wstawiono podsumowanie wyniku Centrum. Uzupełnij dane klienta i test końcowy; sprawdź treść przed zapisem.")

    def record(self):
        values = {}
        for name, widget in self.fields.items():
            if name == "data":
                values[name] = widget.date().toString("yyyy-MM-dd")
            elif name == "czas_pracy_min":
                values[name] = widget.value()
            elif name == "czesci":
                values[name] = [line.strip() for line in widget.toPlainText().splitlines() if line.strip()]
            elif isinstance(widget, QTextEdit):
                values[name] = widget.toPlainText()
            else:
                values[name] = widget.text()
        return validate(values)

    def generate(self):
        if self.worker is not None and self.worker.isRunning():
            return
        try:
            record = self.record()
        except (ValueError, TypeError) as error:
            self.status.setText(f"Nieprawidłowy formularz: {error}")
            return
        directory = QFileDialog.getExistingDirectory(self, "Folder gotowego raportu")
        if not directory:
            return
        self.generate_button.setEnabled(False)
        self.status.setText("Zapisuję raport…")
        self.worker = ReportWorker(record, directory, self)
        self.worker.loaded.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.worker.start()

    def show_result(self, result):
        self.status.setText("Zapisano: " + ", ".join(result["files"]))
        if "pdf_error" in result:
            QMessageBox.warning(self, "PDF niedostępny",
                                "Zapisano HTML, JSON i TXT. PDF nie powstał: " + result["pdf_error"])

    def show_error(self, message):
        self.status.setText("Nie zapisano raportu: " + message)

    def show_help(self):
        QMessageBox.information(self, "Pomoc — Repair Report",
                                "Wymagane są numer zlecenia, klient, urządzenie, problem, diagnoza, "
                                "wykonane czynności i test końcowy. Numer, data i technik są wstępnie wypełnione. "
                                "Pliki powstają wyłącznie w wybranym folderze. Raport może zawierać dane prywatne; "
                                "nie wysyłamy go automatycznie do sieci.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Poczekaj na zakończenie zapisu raportu.")
            event.ignore()
            return
        super().closeEvent(event)
