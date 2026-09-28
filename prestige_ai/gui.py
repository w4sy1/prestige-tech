"""Lokalna analiza i jawny podgląd/wywołanie zewnętrznego AI."""

import json
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout)

from prestige_core.ai_service import external, local, preview
from prestige_core.pdf_export import export_pdf
from prestige_core.ui_theme import APP_QSS, center_header


class AiWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, action, source, model, expected_payload=None, parent=None):
        super().__init__(parent)
        self.action, self.source, self.model = action, source, model
        self.expected_payload = expected_payload

    def run(self):
        try:
            if self.action == "local":
                result = local(self.source)
            elif self.action == "preview":
                result = preview(self.source, self.model)
            elif self.action == "external":
                result = external(self.source, self.model,
                                  expected_payload=self.expected_payload)
            else:
                raise ValueError("Nieznana operacja AI.")
            self.loaded.emit({"action": self.action, "result": result})
        except (OSError, ValueError, RuntimeError, TypeError, KeyError) as error:
            self.failed.emit(str(error))


class AiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PRESTIGE TECH — AI Diagnostic Assistant")
        self.resize(820, 640)
        self.setMinimumSize(650, 480)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        self.preview_payload = None
        self.preview_source = None
        self.preview_model = None
        self.last_result = None
        layout = QVBoxLayout(self)
        layout.addWidget(center_header("AI Diagnostic Assistant", "Raport JSON z dowolnego Centrum. Tryb lokalny niczego nie wysyła."))
        row = QHBoxLayout()
        self.source = QLineEdit()
        self.source.setPlaceholderText("Wybierz raport JSON")
        self.source.textChanged.connect(self.clear_preview)
        row.addWidget(self.source, 1)
        choose = QPushButton("Wybierz…")
        choose.clicked.connect(self.choose_source)
        row.addWidget(choose)
        layout.addLayout(row)
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model zewnętrzny"))
        self.model = QLineEdit("gpt-5-mini")
        self.model.textChanged.connect(self.clear_preview)
        model_row.addWidget(self.model)
        layout.addLayout(model_row)
        actions = QHBoxLayout()
        self.local_button = QPushButton("Analiza lokalna")
        self.local_button.clicked.connect(lambda: self.start("local"))
        actions.addWidget(self.local_button)
        self.preview_button = QPushButton("Pokaż dane do wysłania")
        self.preview_button.clicked.connect(lambda: self.start("preview"))
        actions.addWidget(self.preview_button)
        self.external_button = QPushButton("Wyślij do zewnętrznego AI")
        self.external_button.setEnabled(False)
        self.external_button.clicked.connect(self.confirm_external)
        actions.addWidget(self.external_button)
        layout.addLayout(actions)
        exports = QHBoxLayout()
        self.json_button = QPushButton("Zapisz wynik JSON")
        self.json_button.clicked.connect(self.save_json)
        self.json_button.setEnabled(False)
        exports.addWidget(self.json_button)
        self.pdf_button = QPushButton("Eksport PDF")
        self.pdf_button.clicked.connect(self.save_pdf)
        self.pdf_button.setEnabled(False)
        exports.addWidget(self.pdf_button)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        exports.addWidget(self.help_button)
        layout.addLayout(exports)
        self.status = QLabel("Wybierz raport. Podgląd musi poprzedzać wysłanie.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

    def choose_source(self):
        path, _ = QFileDialog.getOpenFileName(self, "Raport Centrum", "", "JSON (*.json)")
        if path:
            self.source.setText(path)

    def clear_preview(self):
        self.preview_payload = self.preview_source = self.preview_model = None
        self.external_button.setEnabled(False)

    def start(self, action):
        if self.worker is not None and self.worker.isRunning():
            return
        source, model = self.source.text().strip(), self.model.text().strip()
        if not source:
            self.show_error("Wybierz raport JSON.")
            return
        if action == "external" and (self.preview_payload is None
                                     or source != self.preview_source or model != self.preview_model):
            self.show_error("Najpierw pokaż aktualne dane do wysłania.")
            return
        self.set_buttons(False)
        self.status.setText("Trwa analiza…")
        self.worker = AiWorker(action, source, model, self.preview_payload, self)
        self.worker.loaded.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(lambda: self.set_buttons(True))
        self.worker.start()

    def set_buttons(self, enabled):
        self.source.setEnabled(enabled)
        self.model.setEnabled(enabled)
        self.local_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.external_button.setEnabled(enabled and self.preview_payload is not None)

    def confirm_external(self):
        if self.preview_payload is None:
            return
        answer = QMessageBox.question(self, "Zewnętrzne AI",
                                      "Wyślij pokazane metryki do OpenAI? Może to generować koszt API. "
                                      "Wynik modelu wymaga weryfikacji.",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.start("external")

    def show_result(self, data):
        action, result = data["action"], data["result"]
        if action == "preview":
            self.preview_payload = result["preview"]
            self.preview_source = self.worker.source
            self.preview_model = self.worker.model
            self.status.setText("Podgląd gotowy. Dopiero potwierdzenie wyśle pokazane metryki.")
        else:
            self.status.setText("Analiza ukończona: " + result["mode"])
            self.last_result = result
            self.json_button.setEnabled(True)
            self.pdf_button.setEnabled(True)
        self.output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    def show_error(self, message):
        self.status.setText("Analiza nieukończona.")
        self.output.setPlainText(message)

    def save_json(self):
        if self.last_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Nowy wynik AI", "ai-analysis.json", "JSON (*.json)")
        if path:
            try:
                with Path(path).open("x", encoding="utf-8") as stream:
                    json.dump(self.last_result, stream, ensure_ascii=False, indent=2)
            except (OSError, TypeError, ValueError) as error:
                self.show_error(str(error))
            else:
                self.status.setText("Zapisano: " + path)

    def save_pdf(self):
        if self.last_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Nowy wynik AI PDF", "ai-analysis.pdf", "PDF (*.pdf)")
        if path:
            try:
                export_pdf(self.last_result, path, "Analiza diagnostyczna AI")
            except (OSError, ValueError, RuntimeError) as error:
                self.show_error(str(error))
            else:
                self.status.setText("Zapisano: " + path)

    def show_help(self):
        QMessageBox.information(self, "Pomoc — AI Diagnostic Assistant",
                                "LOCAL MODE analizuje raport lokalnie regułami. Wynik jest wskazówką, nie diagnozą. "
                                "Podgląd pokazuje pełne żądanie zewnętrzne; alerty opisowe są z niego usuwane. "
                                "Wysyłka wymaga OPENAI_API_KEY w środowisku i osobnego potwierdzenia. "
                                "Zmiana raportu lub modelu wymaga nowego podglądu. Raport może zawierać dane prywatne.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Poczekaj na zakończenie analizy przed zamknięciem.")
            event.ignore()
            return
        super().closeEvent(event)
