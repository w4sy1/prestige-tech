"""Wielokrotnego użytku formularz Repair Report dla Centrów."""

from datetime import date
from pathlib import Path
import uuid

from PySide6.QtCore import QDate, QThread, Signal
from PySide6.QtWidgets import (QComboBox, QDateEdit, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
                               QSpinBox, QTextEdit, QVBoxLayout, QWidget)

from prestige_core.pdf_export import export_pdf
from prestige_core.report_service import LABELS, render, template, validate
from prestige_core.report_service import missing_fields
from prestige_core.report_attachments import attachment_manifest
from prestige_core.report_evidence import import_center_json
from prestige_core.family_summary import build_family_summary, render_family_text, save_family_text
from prestige_core.ui_theme import APP_QSS, center_header


LONG_FIELDS = frozenset(("zgloszony_problem", "diagnoza", "wykonane_czynnosci",
                         "zalecenia", "test_koncowy", "czesci"))


class ReportWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, record, directory, attachments=(), imported_sources=(), parent=None):
        super().__init__(parent)
        self.record, self.directory = record, directory
        self.attachments = attachments
        self.imported_sources = imported_sources

    def run(self):
        try:
            for path, expected_hash in self.imported_sources:
                if import_center_json(path)["sha256"] != expected_hash:
                    raise ValueError("Zaimportowany wynik Centrum zmienił się; wybierz go ponownie.")
            result = render(self.record, self.directory)
            if self.attachments:
                manifest = Path(result["files"][0]).with_suffix(".attachments.json")
                try:
                    result["files"].append(attachment_manifest(self.attachments, manifest))
                except (OSError, ValueError) as error:
                    result["attachment_error"] = str(error)
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
        self.attachments = []
        self.imported_sources = {}
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
            elif name == "status_weryfikacji":
                widget = QComboBox()
                widget.addItems((defaults[name], "Potwierdzona — test po naprawie wykonano i opisano"))
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
        evidence_actions = QHBoxLayout()
        preview_button = QPushButton("Sprawdź brakujące pola")
        preview_button.clicked.connect(self.preview_fields)
        actions.addWidget(preview_button)
        attachments_button = QPushButton("Wybierz załączniki")
        attachments_button.clicked.connect(self.choose_attachments)
        evidence_actions.addWidget(attachments_button)
        import_button = QPushButton("Importuj wynik Centrum JSON")
        import_button.clicked.connect(self.import_center_result)
        evidence_actions.addWidget(import_button)
        family_button = QPushButton("Raport stanu dla bliskiej osoby")
        family_button.clicked.connect(self.create_family_summary)
        evidence_actions.addWidget(family_button)
        self.generate_button = QPushButton("Zapisz HTML / JSON / TXT / PDF")
        self.generate_button.clicked.connect(self.generate)
        actions.addWidget(self.generate_button)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        actions.addWidget(self.help_button)
        main.addLayout(evidence_actions)
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

    def create_family_summary(self):
        directory = QFileDialog.getExistingDirectory(self, "Katalog zapisanych przeglądów komputera")
        if not directory:
            return
        try:
            summary = build_family_summary(directory)
        except (OSError, ValueError) as error:
            self.status.setText("Nie przygotowano raportu: " + str(error))
            return
        preview = render_family_text(summary)
        if QMessageBox.question(self, "Sprawdź treść raportu", preview + "\nZapisać ten raport?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Nowy raport dla bliskiej osoby",
                                                     "stan-komputera.txt", "Tekst (*.txt)")
        if not destination:
            return
        try:
            saved = save_family_text(summary, destination)
        except (OSError, ValueError) as error:
            self.status.setText("Nie zapisano raportu: " + str(error))
            return
        self.status.setText(f"Zapisano lokalnie: {saved}. Raportu nie wysłano.")

    def record(self):
        values = self.form_values()
        return validate(values)

    def form_values(self):
        values = {}
        for name, widget in self.fields.items():
            if name == "data":
                values[name] = widget.date().toString("yyyy-MM-dd")
            elif name == "czas_pracy_min":
                values[name] = widget.value()
            elif name == "status_weryfikacji":
                values[name] = widget.currentText()
            elif name == "czesci":
                values[name] = [line.strip() for line in widget.toPlainText().splitlines() if line.strip()]
            elif isinstance(widget, QTextEdit):
                values[name] = widget.toPlainText()
            else:
                values[name] = widget.text()
        return values

    def preview_fields(self):
        missing = missing_fields(self.form_values())
        self.status.setText("Brakujące pola: " + ", ".join(missing) if missing
                            else "Wszystkie wymagane pola są wypełnione; sprawdź poprawność treści przed zapisem.")

    def choose_attachments(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Pliki do manifestu SHA-256 (maks. 20)")
        if paths:
            imported = list(self.imported_sources)
            selected = [str(Path(path).resolve()) for path in paths]
            self.attachments = list(dict.fromkeys(imported + selected))[:20]
            self.status.setText(f"Wybrano {len(self.attachments)} plików; raport zapisze ich nazwy, rozmiary i SHA-256, bez kopiowania.")

    def import_center_result(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wynik Centrum", "", "JSON (*.json)")
        if not path:
            return
        try:
            evidence = import_center_json(path)
        except (OSError, ValueError, UnicodeError) as error:
            self.status.setText("Nie zaimportowano wyniku: " + str(error))
            return
        source = evidence["path"]
        if source not in self.attachments and len(self.attachments) >= 20:
            self.status.setText("Limit 20 odniesień do załączników; usuń inne przed importem.")
            return
        answer = QMessageBox.question(
            self, "Import wyniku Centrum",
            evidence["center"] + "\n" + evidence["summary"] + "\nSHA-256: "
            + evidence["sha256"] + "\n\nDodać neutralny opis do czynności i źródło do manifestu?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        if source in self.imported_sources:
            self.status.setText("Ten wynik jest już zaimportowany.")
            return
        if source not in self.attachments:
            self.attachments.append(source)
        self.imported_sources[source] = evidence["sha256"]
        current = self.fields["wykonane_czynnosci"].toPlainText().strip()
        note = evidence["center"] + ": " + evidence["summary"]
        self.fields["wykonane_czynnosci"].setPlainText(
            (current + "\n" if current else "") + note)
        self.status.setText("Zaimportowano odczyt. Uzupełnij diagnozę i test końcowy; źródło zostanie sprawdzone przed zapisem.")

    def generate(self):
        if self.worker is not None and self.worker.isRunning():
            return
        try:
            record = self.record()
        except (ValueError, TypeError) as error:
            self.status.setText(f"Nieprawidłowy formularz: {error}")
            return
        if (record["status_weryfikacji"].startswith("Potwierdzona")
                and len(record["test_koncowy"].strip()) < 20):
            self.status.setText("Opisz wykonany test końcowy i jego wynik (co najmniej 20 znaków), "
                                "zanim oznaczysz naprawę jako potwierdzoną.")
            return
        directory = QFileDialog.getExistingDirectory(self, "Folder gotowego raportu")
        if not directory:
            return
        self.generate_button.setEnabled(False)
        self.status.setText("Zapisuję raport…")
        self.worker = ReportWorker(record, directory, tuple(self.attachments),
                                   tuple(self.imported_sources.items()), self)
        self.worker.loaded.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.worker.start()

    def show_result(self, result):
        self.status.setText("Zapisano: " + ", ".join(result["files"]))
        if "attachment_error" in result:
            QMessageBox.warning(self, "Manifest załączników niedostępny",
                                "Raport zapisano, ale manifest SHA-256 nie powstał: " + result["attachment_error"])
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
                                "nie wysyłamy go automatycznie do sieci. Import wyników JSON dopisuje tylko neutralny "
                                "opis i odniesienie SHA-256; diagnozę oraz test końcowy wypełnia technik.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Poczekaj na zakończenie zapisu raportu.")
            event.ignore()
            return
        super().closeEvent(event)
