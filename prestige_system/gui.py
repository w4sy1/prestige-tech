"""Pierwsza karta System Center: migawka Windows i porównanie dwóch plików."""

import json
from pathlib import Path
import uuid

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from prestige_core.system_snapshot import collect, compare, load_snapshot, save_snapshot
from prestige_core.windows_toolkit import collect as collect_toolkit
from prestige_core.windows_repairs import OPERATIONS, plan_repair, run_repair
from prestige_core.pc_cleanup import clean, profiles, restore, scan, scan_recycle
from prestige_core.ui_theme import APP_QSS, COLORS
from prestige_report.gui import ReportDialog
from prestige_core.report_prefill import summarize_center_result
from prestige_ai.gui import AiDialog


class SnapshotWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, action, paths, parent=None):
        super().__init__(parent)
        self.action, self.paths = action, paths

    def run(self):
        try:
            if self.action == "capture":
                data = collect()
                destination = save_snapshot(data, self.paths[0])
                result = {"action": "capture", "path": destination,
                          "sections": len(data["sections"]),
                          "unknown": sum(row["status"] != "OK" for row in data["sections"].values())}
            elif self.action == "compare":
                result = {"action": "compare", "comparison": compare(
                    load_snapshot(self.paths[0]), load_snapshot(self.paths[1]))}
            elif self.action == "toolkit":
                result = {"action": "toolkit", "diagnostic": collect_toolkit()}
            else:
                raise ValueError("Nieznana operacja System Center.")
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError, TypeError) as error:
            self.failed.emit(str(error))


class CleanupWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, action, *, profile=None, days=7, plan=None, directory=None, parent=None):
        super().__init__(parent)
        self.action, self.profile, self.days = action, profile, days
        self.plan, self.directory = plan, directory

    def run(self):
        try:
            if self.action == "scan":
                available = profiles()
                if self.profile not in available:
                    raise ValueError("Profil nie jest dostępny w tym systemie.")
                if self.profile == "recycle-bin":
                    result = scan_recycle()
                else:
                    result = scan(available[self.profile], self.days)
                    if self.profile == "thumbnails":
                        result["files"] = [row for row in result["files"] if row["clean_allowed"]]
                        result["total_bytes"] = sum(row["size"] for row in result["files"])
                        result["clean_allowed"] = True
            elif self.action == "clean":
                result = clean(self.plan, self.directory)
            elif self.action == "restore":
                result = restore(self.directory)
            else:
                raise ValueError("Nieznana operacja PC Cleanup.")
            self.loaded.emit({"action": self.action, "result": result})
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
            self.failed.emit(str(error))


class RepairWorker(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, directory, parent=None):
        super().__init__(parent)
        self.operation, self.directory = operation, directory

    def run(self):
        try:
            self.loaded.emit(run_repair(self.operation, self.directory,
                                        accept_no_rollback=True))
        except (OSError, ValueError, RuntimeError, PermissionError) as error:
            self.failed.emit(str(error))


class SystemCenterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRESTIGE TECH — System Center")
        self.resize(900, 650)
        self.setMinimumSize(700, 500)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        self.cleanup_worker = None
        self.repair_worker = None
        self.cleanup_plan = None
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
        title = QLabel("System Center")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        main.addWidget(title)
        main.addWidget(QLabel("Migawka Windows, aktualizacje i kontrolowane czyszczenie."))
        controls = QHBoxLayout()
        self.capture_button = QPushButton("Zapisz nową migawkę")
        self.capture_button.clicked.connect(self.choose_capture)
        controls.addWidget(self.capture_button)
        self.compare_button = QPushButton("Porównaj dwie migawki")
        self.compare_button.clicked.connect(self.choose_compare)
        controls.addWidget(self.compare_button)
        self.toolkit_button = QPushButton("Diagnostyka Windows Toolkit")
        self.toolkit_button.clicked.connect(lambda: self._start("toolkit", ()))
        controls.addWidget(self.toolkit_button)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        controls.addWidget(self.help_button)
        self.report_button = QPushButton("Raport serwisowy")
        self.report_button.clicked.connect(self.open_report)
        controls.addWidget(self.report_button)
        self.ai_button = QPushButton("Analiza AI")
        self.ai_button.clicked.connect(self.open_ai)
        controls.addWidget(self.ai_button)
        main.addLayout(controls)
        repair_controls = QHBoxLayout()
        self.repair_operation = QComboBox()
        for operation in OPERATIONS:
            self.repair_operation.addItem(operation, operation)
        repair_controls.addWidget(self.repair_operation)
        self.repair_plan_button = QPushButton("Plan naprawy")
        self.repair_plan_button.clicked.connect(self.show_repair_plan)
        repair_controls.addWidget(self.repair_plan_button)
        self.repair_run_button = QPushButton("Wykonaj naprawę")
        self.repair_run_button.clicked.connect(self.start_repair)
        repair_controls.addWidget(self.repair_run_button)
        main.addLayout(repair_controls)
        cleanup_controls = QHBoxLayout()
        self.cleanup_profile = QComboBox()
        self.cleanup_profile.addItems(profiles())
        cleanup_controls.addWidget(self.cleanup_profile)
        self.cleanup_days = QSpinBox()
        self.cleanup_days.setRange(1, 3650)
        self.cleanup_days.setValue(7)
        self.cleanup_days.setSuffix(" dni")
        cleanup_controls.addWidget(self.cleanup_days)
        self.cleanup_scan_button = QPushButton("Skan PC Cleanup")
        self.cleanup_scan_button.clicked.connect(self.start_cleanup_scan)
        cleanup_controls.addWidget(self.cleanup_scan_button)
        self.cleanup_apply_button = QPushButton("Przenieś do kwarantanny")
        self.cleanup_apply_button.setEnabled(False)
        self.cleanup_apply_button.clicked.connect(self.choose_cleanup_apply)
        cleanup_controls.addWidget(self.cleanup_apply_button)
        self.cleanup_restore_button = QPushButton("Przywróć z kwarantanny")
        self.cleanup_restore_button.clicked.connect(self.choose_cleanup_restore)
        cleanup_controls.addWidget(self.cleanup_restore_button)
        main.addLayout(cleanup_controls)
        self.status = QLabel("Wybierz operację.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        card_layout.addWidget(self.result)
        main.addWidget(card, 1)

    def choose_capture(self):
        destination, _ = QFileDialog.getSaveFileName(self, "Nowy plik migawki", "system-snapshot.json", "JSON (*.json)")
        if destination:
            self._start("capture", (destination,))

    def choose_compare(self):
        before, _ = QFileDialog.getOpenFileName(self, "Starsza migawka", "", "JSON (*.json)")
        if not before:
            return
        after, _ = QFileDialog.getOpenFileName(self, "Nowsza migawka", "", "JSON (*.json)")
        if after:
            self._start("compare", (before, after))

    def _start(self, action, paths):
        if self._busy():
            return
        self.capture_button.setEnabled(False)
        self.compare_button.setEnabled(False)
        self.toolkit_button.setEnabled(False)
        self.status.setText("Trwa odczyt…")
        self.worker = SnapshotWorker(action, paths, self)
        self.worker.loaded.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def _busy(self):
        return ((self.worker is not None and self.worker.isRunning())
                or (self.cleanup_worker is not None and self.cleanup_worker.isRunning())
                or (self.repair_worker is not None and self.repair_worker.isRunning()))

    def show_repair_plan(self):
        plan = plan_repair(self.repair_operation.currentData())
        self.result.setPlainText(json.dumps(plan, ensure_ascii=False, indent=2))
        self.status.setText("Plan bez wykonania. Operacja nie ma gwarantowanego cofnięcia.")

    def start_repair(self):
        if self._busy():
            return
        operation = self.repair_operation.currentData()
        plan = plan_repair(operation)
        directory = QFileDialog.getExistingDirectory(self, "Katalog na dziennik i migawkę diagnostyczną")
        if not directory:
            return
        answer = QMessageBox.question(
            self, "Naprawa Windows bez rollbacku",
            f"Uruchomić {' '.join(plan['command'])}?\n{plan['description']}\n"
            "Wymagany administrator. Program zapisze dziennik i diagnostykę przed wykonaniem. "
            "Nie ma gwarantowanego cofnięcia; połączenie sieciowe może zostać przerwane.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.repair_plan_button.setEnabled(False)
        self.repair_run_button.setEnabled(False)
        self.status.setText(f"Wykonuję {operation}; nie zamykaj okna przed zakończeniem.")
        self.repair_worker = RepairWorker(operation, directory, self)
        self.repair_worker.loaded.connect(self.show_repair_result)
        self.repair_worker.failed.connect(self.show_repair_error)
        self.repair_worker.finished.connect(self.finish_repair)
        self.repair_worker.start()

    def show_repair_result(self, result):
        try:
            self.report_prefill = summarize_center_result("System", "repair", result)
        except (ValueError, KeyError, TypeError):
            self.report_prefill = None
        self.result.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        self.status.setText(f"Naprawa {result['operation']}: {result['status']}; dziennik: {result['journal']}")

    def show_repair_error(self, message):
        self.report_prefill = None
        self.status.setText("Naprawa nie została ukończona: " + message)

    def finish_repair(self):
        self.repair_plan_button.setEnabled(True)
        self.repair_run_button.setEnabled(True)

    def start_cleanup_scan(self):
        if self._busy():
            return
        self.cleanup_plan = None
        self.cleanup_apply_button.setEnabled(False)
        self.cleanup_profile.setEnabled(False)
        self.cleanup_scan_button.setEnabled(False)
        self.status.setText("Trwa skan PC Cleanup…")
        self.cleanup_worker = CleanupWorker("scan", profile=self.cleanup_profile.currentText(),
                                            days=self.cleanup_days.value(), parent=self)
        self.cleanup_worker.loaded.connect(self.show_cleanup_result)
        self.cleanup_worker.failed.connect(self.show_error)
        self.cleanup_worker.finished.connect(self._cleanup_finished)
        self.cleanup_worker.start()

    def choose_cleanup_apply(self):
        if self._busy() or not self.cleanup_plan or not self.cleanup_plan.get("clean_allowed"):
            return
        parent = QFileDialog.getExistingDirectory(self, "Katalog nadrzędny dla nowej kwarantanny")
        if not parent:
            return
        destination = str(Path(parent) / ("prestige-quarantine-" + uuid.uuid4().hex))
        count = len(self.cleanup_plan["files"])
        answer = QMessageBox.question(self, "Potwierdź kwarantannę",
                                      f"Przenieść {count} plików do nowej kwarantanny?\n{destination}",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self._start_cleanup_change("clean", plan=self.cleanup_plan, directory=destination)

    def choose_cleanup_restore(self):
        if self._busy():
            return
        directory = QFileDialog.getExistingDirectory(self, "Kwarantanna do przywrócenia")
        if not directory:
            return
        answer = QMessageBox.question(self, "Potwierdź przywrócenie",
                                      f"Przywrócić pliki z kwarantanny?\n{directory}",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self._start_cleanup_change("restore", directory=directory)

    def _start_cleanup_change(self, action, *, plan=None, directory=None):
        self.cleanup_apply_button.setEnabled(False)
        self.cleanup_restore_button.setEnabled(False)
        self.status.setText("Trwa operacja PC Cleanup…")
        self.cleanup_worker = CleanupWorker(action, plan=plan, directory=directory, parent=self)
        self.cleanup_worker.loaded.connect(self.show_cleanup_result)
        self.cleanup_worker.failed.connect(self.show_error)
        self.cleanup_worker.finished.connect(self._cleanup_finished)
        self.cleanup_worker.start()

    def show_cleanup_result(self, data):
        try:
            self.report_prefill = summarize_center_result("System", data["action"], data)
        except (ValueError, KeyError, TypeError):
            self.report_prefill = None
        result = data["result"]
        if data["action"] == "scan":
            self.cleanup_plan = result
            allowed = result.get("clean_allowed", False) and bool(result.get("files"))
            self.cleanup_apply_button.setEnabled(allowed)
            self.status.setText(f"Skan zakończony. Plików: {len(result.get('files', result.get('items', [])))}; "
                                f"kwarantanna {'dozwolona' if allowed else 'niedozwolona'}.")
        elif data["action"] == "clean":
            self.cleanup_plan = None
            self.status.setText(f"Przeniesiono {result['moved']} plików. Kwarantanna: {result['quarantine']}")
        else:
            self.status.setText(f"Przywrócono {result['restored']} plików; już przywróconych: {result['already_restored']}.")
        self.result.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))

    def _cleanup_finished(self):
        self.cleanup_profile.setEnabled(True)
        self.cleanup_scan_button.setEnabled(True)
        self.cleanup_restore_button.setEnabled(True)

    def _finished(self):
        self.capture_button.setEnabled(True)
        self.compare_button.setEnabled(True)
        self.toolkit_button.setEnabled(True)

    def show_result(self, data):
        try:
            self.report_prefill = summarize_center_result("System", data["action"], data)
        except (ValueError, KeyError, TypeError):
            self.report_prefill = None
        if data["action"] == "capture":
            self.status.setText(f"Zapisano: {data['path']}; sekcje UNKNOWN: {data['unknown']}.")
        elif data["action"] == "compare":
            unknown = sum(row["status"] == "UNKNOWN" for row in data["comparison"]["sections"].values())
            self.status.setText(f"Porównano migawki; sekcje UNKNOWN: {unknown}.")
        else:
            sections = data["diagnostic"]["sections"]
            unknown = sum(row["status"] == "UNKNOWN" for row in sections.values())
            self.status.setText(f"Diagnostyka Windows: {len(sections)} sekcji; UNKNOWN: {unknown}.")
        self.result.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))

    def show_error(self, message):
        self.report_prefill = None
        self.status.setText("Nie ukończono operacji.")
        self.result.setPlainText(message)

    def show_help(self):
        QMessageBox.information(self, "Pomoc — System Center",
                                "Migawka odczytuje stan Windows bez zmian systemu. Zapis tworzy wyłącznie nowy plik. "
                                "UNKNOWN oznacza niedostępny odczyt, a nie brak problemu. Porównanie procesów i wolnego "
                                "miejsca może wykazać zwykłe zmiany w czasie. Plik migawki może zawierać prywatne dane. "
                                "PC Cleanup najpierw skanuje i pokazuje plan. Kwarantanna jest dostępna tylko dla "
                                "zatwierdzonych TEMP/cache; Downloads, logi i Kosz są do analizy. Diagnostyka aktualizacji "
                                "czyta historię, usługi, polityki i sygnały restartu bez wyszukiwania nowych aktualizacji. Przed przeniesieniem "
                                "każdy plik jest ponownie sprawdzany. Przywrócenie nie nadpisuje nowszych plików. "
                                "SFC, DISM i naprawy sieci wymagają administratora, osobnej zgody i dziennika; nie mają gwarantowanego cofnięcia.")

    def closeEvent(self, event):
        if self._busy():
            self.status.setText("Poczekaj na zakończenie operacji przed zamknięciem.")
            event.ignore()
            return
        super().closeEvent(event)

    def open_report(self):
        self.report_dialog = ReportDialog(self, prefill=self.report_prefill)
        self.report_dialog.show()

    def open_ai(self):
        self.ai_dialog = AiDialog(self)
        self.ai_dialog.show()
