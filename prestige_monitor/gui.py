"""Odczytowy Monitor: skan i porównanie bez zmian w katalogu źródłowym."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
from threading import Event

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
    QTabWidget, QLineEdit, QCheckBox, QInputDialog, QComboBox, QPlainTextEdit,
)

from prestige_core.event_history import EventJournal, append_comparison, load_history, load_journal, new_history, save_history
from prestige_core.baseline_update import update_baseline
from prestige_core.legacy_integrity import convert_baseline
from prestige_core.file_snapshot import classify_file_events, compare_files, scan_files
from prestige_core.network_snapshot import save_snapshot
from prestige_core.native_events import NativeEventStream, collect_native_events
from prestige_core.native_correlation import correlate_extended
from prestige_core.ui_theme import APP_QSS, COLORS
from prestige_core.watch_state import WatchStateStore
from prestige_core.watch_state_import import import_legacy_watch_database
from prestige_core.baseline_signing import new_key, sign, verify
from prestige_core.hashing import FileHashService
from prestige_core.hash_manifest import compare_manifests, compatible_manifest, make_manifest, save_manifest, validate_manifest


class ScanWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, root, parent=None, extended=False):
        super().__init__(parent)
        self.root = root
        self.extended = extended
        self.cancel_event = Event()

    def run(self):
        try:
            self.loaded.emit(scan_files(self.root, cancel_event=self.cancel_event,
                                        extended=self.extended))
        except (OSError, ValueError) as error:
            self.failed.emit(str(error))


class WatchWorker(QThread):
    changed = Signal(dict)
    failed = Signal(str)
    FULL_REHASH_EVERY = 30

    def __init__(self, root, parent=None, state_path=None, extended=False):
        super().__init__(parent)
        self.root = root
        self.stop_event = Event()
        self.state_path = state_path
        self.extended = extended

    def run(self):
        store = None
        try:
            if self.state_path is not None:
                store = WatchStateStore(self.root, self.state_path)
            previous = store.load() if store is not None else None
            if previous is not None and bool(previous.get("options", {}).get("extended", False)) != self.extended:
                self.failed.emit("Baza SQLite ma inny tryb ACL/ADS; wybierz osobną bazę albo zgodny tryb.")
                return
            initial = scan_files(self.root, previous=previous,
                                 force_rehash=previous is not None,
                                 cancel_event=self.stop_event, extended=self.extended)
            if not initial["complete"]:
                self.failed.emit("Początkowy skan jest niepełny; obserwacja nie wystartowała.")
                return
            if previous is not None:
                restored = classify_file_events(previous, initial)
                if restored["status"] != "COMPLETE":
                    self.failed.emit("UNKNOWN: niepełne porównanie po wznowieniu bazy.")
                    return
                store.record(initial, restored)
                if (restored["added"] or restored["removed"] or restored["changed"]
                        or restored["renamed"]):
                    self.changed.emit(restored)
            elif store is not None:
                store.record(initial)
            previous = initial
            scan_count = 0
            while not self.stop_event.wait(2.0):
                scan_count += 1
                current = scan_files(
                    self.root, previous=previous, cancel_event=self.stop_event,
                    force_rehash=scan_count % self.FULL_REHASH_EVERY == 0,
                    extended=self.extended,
                )
                result = classify_file_events(previous, current)
                if result["status"] != "COMPLETE":
                    if not self.stop_event.is_set():
                        self.failed.emit("UNKNOWN: odczyt katalogu jest niepełny; obserwacja została zatrzymana.")
                    return
                if store is not None:
                    store.record(current, result)
                if result["added"] or result["removed"] or result["changed"] or result["renamed"]:
                    self.changed.emit(result)
                previous = current
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
            self.failed.emit(str(error))
        finally:
            if store is not None:
                store.close()


class NativeCaptureWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.root = root

    def run(self):
        try:
            self.loaded.emit(collect_native_events(self.root, 10.0))
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            self.failed.emit(str(error))


class NativeStreamWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, root, parent=None, extended=False):
        super().__init__(parent)
        self.stream = NativeEventStream(root)
        self.extended = extended
        self.previous = None

    def run(self):
        try:
            def on_ready():
                if self.extended:
                    self.previous = scan_files(self.stream.root, extended=True)
                    if not self.previous["complete"]:
                        raise RuntimeError("UNKNOWN: początkowy odczyt ACL/ADS jest niepełny.")

            def on_batch(result):
                if self.extended and result["status"] == "COMPLETE":
                    current = scan_files(self.stream.root, previous=self.previous, extended=True)
                    result = correlate_extended(result, self.previous, current)
                    if result["status"] == "COMPLETE":
                        self.previous = current
                self.loaded.emit(result)
                if result["status"] != "COMPLETE":
                    raise RuntimeError(result["reason"])

            self.stream.watch(on_batch, on_ready=on_ready)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            self.failed.emit(str(error))

    def stop(self):
        self.stream.stop()


class LegacyImportWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, source, root, destination, parent=None):
        super().__init__(parent)
        self.source = source
        self.root = root
        self.destination = destination

    def run(self):
        try:
            self.loaded.emit(import_legacy_watch_database(self.source, self.root, self.destination))
        except (OSError, ValueError, sqlite3.Error) as error:
            self.failed.emit(str(error))


class HashWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, path, algorithm, parent=None):
        super().__init__(parent)
        self.path, self.algorithm = path, algorithm

    def run(self):
        try:
            self.loaded.emit(FileHashService.hashes(self.path, (self.algorithm,)))
        except (OSError, ValueError) as error:
            self.failed.emit(str(error))


class ManifestWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, root, algorithm, destination=None, baseline=None,
                 other=None, parent=None):
        super().__init__(parent)
        self.root, self.algorithm = root, algorithm
        self.destination, self.baseline = destination, baseline
        self.other = other
        self.cancel_event = Event()

    def run(self):
        try:
            current = make_manifest(self.root, self.algorithm, cancel_event=self.cancel_event)
            if self.other is not None:
                second = make_manifest(self.other, self.algorithm, cancel_event=self.cancel_event)
                self.loaded.emit({"mode": "verified", "result": compare_manifests(current, second)})
            elif self.destination is not None:
                save_manifest(current, self.destination)
                self.loaded.emit({"mode": "saved", "path": self.destination,
                                  "count": len(current["files"])})
            else:
                self.loaded.emit({"mode": "verified", "result": compare_manifests(self.baseline, current)})
        except (OSError, ValueError, KeyError) as error:
            self.failed.emit(str(error))


class MonitorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRESTIGE TECH — Monitor")
        self.resize(1120, 720)
        self.setMinimumSize(820, 560)
        self.setStyleSheet(APP_QSS)
        self.snapshot = None
        self.baseline = None
        self.baseline_path = None
        self.worker = None
        self.watch_worker = None
        self.native_worker = None
        self.native_stream_worker = None
        self.import_worker = None
        self.hash_worker = None
        self.manifest_worker = None
        self.history = None
        self.history_dirty = False
        self.journal = None
        self.state_path = None

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
        side.addWidget(QLabel("MONITOR"))
        side.addSpacing(28)
        side.addWidget(QLabel("● Integralność plików"))
        side.addStretch()
        side.addWidget(QLabel("By Dominik Wasilak"))
        layout.addWidget(sidebar)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 22, 24, 22)
        title = QLabel("Migawka integralności plików")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        main.addWidget(title)
        main.addWidget(QLabel("Wybierz katalog. Skan liczy SHA-256 bez zmieniania plików źródłowych."))
        self.folder = QLabel("Nie wybrano katalogu")
        self.folder.setWordWrap(True)
        main.addWidget(self.folder)
        actions = QHBoxLayout()
        self.select_button = QPushButton("Wybierz katalog")
        self.select_button.clicked.connect(self.choose_folder)
        actions.addWidget(self.select_button)
        self.scan_button = QPushButton("Skanuj")
        self.scan_button.setEnabled(False)
        self.scan_button.clicked.connect(self.start_scan)
        actions.addWidget(self.scan_button)
        self.extended_checkbox = QCheckBox("ACL/ADS")
        self.extended_checkbox.setToolTip("Dołącz uprawnienia i alternatywne strumienie danych do ręcznego skanu.")
        actions.addWidget(self.extended_checkbox)
        self.cancel_button = QPushButton("Przerwij")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_scan)
        actions.addWidget(self.cancel_button)
        self.watch_button = QPushButton("Obserwuj")
        self.watch_button.setEnabled(False)
        self.watch_button.clicked.connect(self.toggle_watch)
        actions.addWidget(self.watch_button)
        self.native_button = QPushButton("Natywne 10 s")
        self.native_button.setEnabled(False)
        self.native_button.clicked.connect(self.start_native_capture)
        actions.addWidget(self.native_button)
        main.addLayout(actions)
        secondary_actions = QHBoxLayout()
        self.save_button = QPushButton("Zapisz baseline")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_baseline)
        secondary_actions.addWidget(self.save_button)
        self.load_button = QPushButton("Wczytaj baseline")
        self.load_button.clicked.connect(self.load_baseline)
        secondary_actions.addWidget(self.load_button)
        self.update_button = QPushButton("Aktualizuj baseline")
        self.update_button.setEnabled(False)
        self.update_button.clicked.connect(self.update_loaded_baseline)
        secondary_actions.addWidget(self.update_button)
        self.native_stream_button = QPushButton("Natywnie: start")
        self.native_stream_button.setEnabled(False)
        self.native_stream_button.clicked.connect(self.toggle_native_stream)
        secondary_actions.addWidget(self.native_stream_button)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        secondary_actions.addWidget(self.help_button)
        main.addLayout(secondary_actions)
        signing_actions = QHBoxLayout()
        self.key_button = QPushButton("Nowe klucze podpisu")
        self.key_button.clicked.connect(self.generate_signing_keys)
        signing_actions.addWidget(self.key_button)
        self.sign_button = QPushButton("Podpisz baseline")
        self.sign_button.clicked.connect(self.sign_baseline)
        signing_actions.addWidget(self.sign_button)
        self.verify_button = QPushButton("Sprawdź podpis")
        self.verify_button.clicked.connect(self.verify_baseline_signature)
        signing_actions.addWidget(self.verify_button)
        main.addLayout(signing_actions)
        tabs = QTabWidget()
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Plik", "SHA-256", "Wynik"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        card_layout.addWidget(self.table)
        tabs.addTab(card, "Migawka")
        hash_card = QFrame()
        hash_card.setObjectName("Card")
        hash_layout = QVBoxLayout(hash_card)
        hash_actions = QHBoxLayout()
        self.hash_algorithm = QComboBox()
        self.hash_algorithm.addItems(["sha256", "sha512", "sha1", "md5"])
        hash_actions.addWidget(self.hash_algorithm)
        self.hash_expected = QLineEdit()
        self.hash_expected.setPlaceholderText("Oczekiwany hash (opcjonalnie)")
        hash_actions.addWidget(self.hash_expected)
        self.hash_button = QPushButton("Hash pliku")
        self.hash_button.clicked.connect(self.choose_hash_file)
        hash_actions.addWidget(self.hash_button)
        hash_layout.addLayout(hash_actions)
        manifest_actions = QHBoxLayout()
        self.manifest_save_button = QPushButton("Nowy manifest folderu")
        self.manifest_save_button.clicked.connect(self.choose_manifest_generate)
        manifest_actions.addWidget(self.manifest_save_button)
        self.manifest_verify_button = QPushButton("Sprawdź manifest")
        self.manifest_verify_button.clicked.connect(self.choose_manifest_verify)
        manifest_actions.addWidget(self.manifest_verify_button)
        self.compare_folders_button = QPushButton("Porównaj foldery")
        self.compare_folders_button.clicked.connect(self.choose_compare_folders)
        manifest_actions.addWidget(self.compare_folders_button)
        self.manifest_cancel_button = QPushButton("Przerwij")
        self.manifest_cancel_button.setEnabled(False)
        self.manifest_cancel_button.clicked.connect(self.cancel_manifest)
        manifest_actions.addWidget(self.manifest_cancel_button)
        hash_layout.addLayout(manifest_actions)
        self.compare_manifests_button = QPushButton("Porównaj dwa manifesty")
        self.compare_manifests_button.clicked.connect(self.choose_compare_manifests)
        hash_layout.addWidget(self.compare_manifests_button)
        signature_actions = QHBoxLayout()
        self.manifest_sign_button = QPushButton("Podpisz manifest")
        self.manifest_sign_button.clicked.connect(self.sign_manifest)
        signature_actions.addWidget(self.manifest_sign_button)
        self.manifest_signature_button = QPushButton("Sprawdź podpis manifestu")
        self.manifest_signature_button.clicked.connect(self.verify_manifest_signature)
        signature_actions.addWidget(self.manifest_signature_button)
        hash_layout.addLayout(signature_actions)
        self.hash_result = QPlainTextEdit()
        self.hash_result.setReadOnly(True)
        self.hash_result.setPlaceholderText("SHA-256/SHA-512; SHA-1 i MD5 tylko do zgodności ze starszymi danymi.")
        hash_layout.addWidget(self.hash_result, 1)
        tabs.addTab(hash_card, "Hash Checker")
        events_card = QFrame()
        events_card.setObjectName("Card")
        events_layout = QVBoxLayout(events_card)
        self.event_filter = QLineEdit()
        self.event_filter.setPlaceholderText("Filtruj ścieżki zdarzeń")
        self.event_filter.textChanged.connect(self.render_history)
        events_layout.addWidget(self.event_filter)
        history_actions = QHBoxLayout()
        self.history_save_button = QPushButton("Zapisz historię")
        self.history_save_button.setEnabled(False)
        self.history_save_button.clicked.connect(self.save_event_history)
        history_actions.addWidget(self.history_save_button)
        self.history_load_button = QPushButton("Wczytaj historię")
        self.history_load_button.clicked.connect(self.load_event_history)
        history_actions.addWidget(self.history_load_button)
        self.journal_button = QPushButton("Włącz dziennik")
        self.journal_button.setEnabled(False)
        self.journal_button.clicked.connect(self.enable_journal)
        history_actions.addWidget(self.journal_button)
        self.sqlite_button = QPushButton("Baza SQLite")
        self.sqlite_button.setEnabled(False)
        self.sqlite_button.clicked.connect(self.choose_state_database)
        history_actions.addWidget(self.sqlite_button)
        events_layout.addLayout(history_actions)
        self.import_button = QPushButton("Importuj starą bazę SQLite")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.choose_legacy_import)
        events_layout.addWidget(self.import_button)
        self.events_table = QTableWidget(0, 3)
        self.events_table.setHorizontalHeaderLabels(["Czas UTC", "Plik", "Zdarzenie"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.events_table.setEditTriggers(QTableWidget.NoEditTriggers)
        events_layout.addWidget(self.events_table)
        tabs.addTab(events_card, "Zdarzenia")
        main.addWidget(tabs, 1)
        self.status = QLabel("Brak skanu.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        layout.addWidget(content, 1)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz katalog do odczytu")
        if folder:
            try:
                self.set_folder(folder)
            except ValueError as error:
                QMessageBox.warning(self, "Nie zmieniono katalogu", str(error))

    def set_folder(self, folder):
        if self.import_worker is not None and self.import_worker.isRunning():
            raise ValueError("Najpierw zakończ import bazy.")
        if self.native_stream_worker is not None and self.native_stream_worker.isRunning():
            raise ValueError("Najpierw zatrzymaj ciągły odczyt natywny.")
        if self.native_worker is not None and self.native_worker.isRunning():
            raise ValueError("Najpierw zakończ natywny odczyt zdarzeń.")
        if self.watch_worker is not None and self.watch_worker.isRunning():
            raise ValueError("Najpierw zatrzymaj obserwację.")
        if self.worker is not None and self.worker.isRunning():
            raise ValueError("Najpierw zakończ skan.")
        path = Path(folder)
        if not path.is_dir():
            raise ValueError("Wymagany istniejący katalog.")
        if self.history_dirty:
            raise ValueError("Najpierw zapisz bieżącą historię zdarzeń.")
        if self.journal is not None:
            self.journal.close()
            self.journal = None
        self.folder.setText(str(path.resolve()))
        self.history = new_history(path)
        self.history_dirty = False
        self.history_save_button.setEnabled(False)
        self.journal_button.setEnabled(True)
        self.journal_button.setText("Włącz dziennik")
        self.state_path = None
        self.sqlite_button.setEnabled(True)
        self.import_button.setEnabled(True)
        self.sqlite_button.setText("Baza SQLite")
        self.render_history()
        self.snapshot = None
        self.baseline = None
        self.baseline_path = None
        self.save_button.setEnabled(False)
        self.update_button.setEnabled(False)
        self.scan_button.setEnabled(True)
        self.watch_button.setEnabled(True)
        self.native_button.setEnabled(os.name == "nt")
        self.native_stream_button.setEnabled(os.name == "nt")
        self.status.setText("Katalog wybrany. Uruchom skan.")

    def start_scan(self):
        if self.native_stream_worker is not None and self.native_stream_worker.isRunning():
            return
        if self.native_worker is not None and self.native_worker.isRunning():
            return
        if self.watch_worker is not None and self.watch_worker.isRunning():
            return
        if self.worker is not None and self.worker.isRunning():
            return
        if not Path(self.folder.text()).is_dir():
            return
        self.snapshot = None
        self.save_button.setEnabled(False)
        self.update_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("Skanuję pliki…")
        self.worker = ScanWorker(self.folder.text(), self, extended=self.extended_checkbox.isChecked())
        self.worker.loaded.connect(self.show_snapshot)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.finish_scan)
        self.worker.start()

    def cancel_scan(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel_event.set()
            self.status.setText("Przerywam po bieżącym pliku…")

    def finish_scan(self):
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.watch_button.setEnabled(True)

    def toggle_watch(self):
        if self.native_stream_worker is not None and self.native_stream_worker.isRunning():
            return
        if self.native_worker is not None and self.native_worker.isRunning():
            return
        if self.watch_worker is not None and self.watch_worker.isRunning():
            self.watch_worker.stop_event.set()
            self.watch_button.setEnabled(False)
            self.status.setText("Zatrzymuję obserwację…")
            return
        if self.worker is not None and self.worker.isRunning():
            return
        if not Path(self.folder.text()).is_dir():
            return
        self.scan_button.setEnabled(False)
        self.select_button.setEnabled(False)
        self.history_load_button.setEnabled(False)
        self.native_button.setEnabled(False)
        self.native_stream_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self.watch_button.setText("Zatrzymaj")
        self.status.setText("Uruchamiam obserwację. Pierwszy skan może potrwać…")
        self.sqlite_button.setEnabled(False)
        self.watch_worker = WatchWorker(self.folder.text(), self, state_path=self.state_path,
                                        extended=self.extended_checkbox.isChecked())
        self.watch_worker.changed.connect(self.show_events)
        self.watch_worker.failed.connect(self.show_watch_error)
        self.watch_worker.finished.connect(self.finish_watch)
        self.watch_worker.start()

    def show_events(self, result):
        if self.history is None:
            return
        before_count = len(self.history["events"])
        append_comparison(self.history, result)
        self._persist_new_events(before_count)

    def _persist_new_events(self, before_count):
        self.history_dirty = True
        if self.journal is not None:
            try:
                self.journal.append(self.history["events"][before_count:])
                self.history_dirty = False
            except OSError as error:
                if self.watch_worker is not None:
                    self.watch_worker.stop_event.set()
                if self.native_stream_worker is not None:
                    self.native_stream_worker.stop()
                self.status.setText(f"Błąd zapisu dziennika; obserwacja zatrzymana: {error}")
                self.journal.close()
                self.journal = None
                self.journal_button.setEnabled(True)
                self.journal_button.setText("Włącz dziennik")
                self.render_history()
                return False
        self.history_save_button.setEnabled(True)
        self.render_history()
        self.status.setText("Wykryto zmianę. Zdarzenia pochodzą z porównania kolejnych odczytów.")
        return True

    def start_native_capture(self):
        if ((self.native_worker is not None and self.native_worker.isRunning())
                or (self.native_stream_worker is not None and self.native_stream_worker.isRunning())
                or (self.worker is not None and self.worker.isRunning())
                or (self.watch_worker is not None and self.watch_worker.isRunning())):
            return
        if self.history is None:
            return
        self.native_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.watch_button.setEnabled(False)
        self.select_button.setEnabled(False)
        self.history_load_button.setEnabled(False)
        self.sqlite_button.setEnabled(False)
        self.native_stream_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self.status.setText("Natywna obserwacja trwa 10 sekund…")
        self.native_worker = NativeCaptureWorker(self.folder.text(), self)
        self.native_worker.loaded.connect(self.show_native_capture)
        self.native_worker.failed.connect(self.show_watch_error)
        self.native_worker.finished.connect(self.finish_native_capture)
        self.native_worker.start()

    def show_native_capture(self, result):
        if result["status"] != "COMPLETE":
            self.status.setText("UNKNOWN: bufor zdarzeń został przepełniony; wynik odrzucono.")
            return
        rows = result["events"]
        if not rows:
            self.status.setText("Natywny odczyt zakończony: brak zdarzeń w tym oknie czasu.")
            return
        before_count = len(self.history["events"])
        self.history["events"].extend(rows)
        if self._persist_new_events(before_count):
            self.status.setText(f"Natywny odczyt zakończony: {len(rows)} zdarzeń.")

    def finish_native_capture(self):
        self.native_button.setEnabled(os.name == "nt")
        self.scan_button.setEnabled(True)
        self.watch_button.setEnabled(True)
        self.select_button.setEnabled(True)
        self.history_load_button.setEnabled(True)
        self.sqlite_button.setEnabled(True)
        self.native_stream_button.setEnabled(os.name == "nt")
        self.import_button.setEnabled(True)

    def toggle_native_stream(self):
        if self.native_stream_worker is not None and self.native_stream_worker.isRunning():
            self.native_stream_worker.stop()
            self.native_stream_button.setEnabled(False)
            self.status.setText("Zatrzymuję ciągły odczyt natywny…")
            return
        if ((self.worker is not None and self.worker.isRunning())
                or (self.watch_worker is not None and self.watch_worker.isRunning())
                or (self.native_worker is not None and self.native_worker.isRunning())
                or self.history is None):
            return
        self.native_stream_worker = NativeStreamWorker(
            self.folder.text(), self, extended=self.extended_checkbox.isChecked())
        self.native_stream_worker.loaded.connect(self.show_native_stream_batch)
        self.native_stream_worker.failed.connect(self.show_watch_error)
        self.native_stream_worker.finished.connect(self.finish_native_stream)
        self.native_stream_button.setText("Natywnie: stop")
        self.native_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.watch_button.setEnabled(False)
        self.select_button.setEnabled(False)
        self.history_load_button.setEnabled(False)
        self.sqlite_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self.status.setText("Uruchamiam FileSystemWatcher"
                            + (" z korelacją ACL/ADS…" if self.extended_checkbox.isChecked() else "…"))
        self.native_stream_worker.start()

    def show_native_stream_batch(self, result):
        if result["status"] != "COMPLETE":
            self.status.setText("UNKNOWN: " + result.get("reason", "niepełny odczyt zdarzeń."))
            if self.native_stream_worker is not None:
                self.native_stream_worker.stop()
            return
        rows = result["events"]
        if rows and self.history is not None:
            before_count = len(self.history["events"])
            self.history["events"].extend(rows)
            if self._persist_new_events(before_count):
                correlated = sum(bool(row.get("changes")) for row in rows)
                self.status.setText(f"Ciągła obserwacja natywna: zapisano {len(rows)} zdarzeń; "
                                    f"{correlated} z potwierdzoną zmianą ACL/ADS/treści.")

    def finish_native_stream(self):
        self.native_stream_button.setEnabled(os.name == "nt")
        self.native_stream_button.setText("Natywnie: start")
        self.native_button.setEnabled(os.name == "nt")
        self.scan_button.setEnabled(True)
        self.watch_button.setEnabled(True)
        self.select_button.setEnabled(True)
        self.history_load_button.setEnabled(True)
        self.sqlite_button.setEnabled(True)
        self.import_button.setEnabled(True)

    def render_history(self):
        rows = self.history["events"] if self.history is not None else []
        needle = self.event_filter.text().casefold()
        visible = [row for row in rows if needle in row["path"].casefold()
                   or needle in row.get("old_path", "").casefold()]
        self.events_table.setRowCount(len(visible))
        for index, row in enumerate(visible):
            path_label = (f"{row['old_path']} → {row['path']}"
                          if row.get("old_path") else row["path"])
            label = row["kind"] + (" (" + ", ".join(row["changes"]) + ")"
                                   if row.get("changes") else "")
            for column, value in enumerate((row["at_utc"], path_label, label)):
                self.events_table.setItem(index, column, QTableWidgetItem(value))

    def save_event_history(self):
        if self.history is None or not self.history["events"]:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz historię", "monitor-history.json", "JSON (*.json)")
        if not path:
            return
        try:
            save_history(self.history, path)
        except (FileExistsError, OSError, ValueError) as error:
            QMessageBox.warning(self, "Nie zapisano historii", str(error))
            return
        self.history_dirty = False
        self.status.setText(f"Historia zapisana: {path}")

    def enable_journal(self):
        if self.history is None or self.journal is not None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Nowy dziennik poza obserwowanym katalogiem", "monitor-journal.jsonl", "JSON Lines (*.jsonl)")
        if not path:
            return
        try:
            self.journal = EventJournal(self.history, path)
        except (FileExistsError, OSError, ValueError) as error:
            QMessageBox.warning(self, "Nie włączono dziennika", str(error))
            return
        self.history_dirty = False
        self.journal_button.setEnabled(False)
        self.journal_button.setText("Dziennik aktywny")
        self.status.setText(f"Dziennik aktywny: {path}")

    def load_event_history(self):
        if self.history_dirty:
            QMessageBox.warning(self, "Nie wczytano historii", "Najpierw zapisz bieżącą historię zdarzeń.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Wczytaj historię", "", "Historia (*.json *.jsonl)")
        if not path:
            return
        try:
            history = load_journal(path) if Path(path).suffix.lower() == ".jsonl" else load_history(path)
            if self.history is not None and history["root"] != self.history["root"]:
                raise ValueError("Historia dotyczy innego katalogu.")
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.warning(self, "Nie wczytano historii", str(error))
            return
        self.history = history
        if self.journal is not None:
            self.journal.close()
            self.journal = None
        self.history_dirty = False
        self.folder.setText(history["root"])
        self.scan_button.setEnabled(Path(history["root"]).is_dir())
        self.watch_button.setEnabled(Path(history["root"]).is_dir())
        self.native_button.setEnabled(os.name == "nt" and Path(history["root"]).is_dir())
        self.native_stream_button.setEnabled(os.name == "nt" and Path(history["root"]).is_dir())
        self.history_save_button.setEnabled(bool(history["events"]))
        self.journal_button.setEnabled(True)
        self.journal_button.setText("Włącz dziennik")
        self.render_history()
        self.status.setText(f"Historia wczytana: {path}")

    def show_watch_error(self, message):
        self.status.setText(message)

    def finish_watch(self):
        self.scan_button.setEnabled(True)
        self.select_button.setEnabled(True)
        self.history_load_button.setEnabled(True)
        self.watch_button.setEnabled(True)
        self.watch_button.setText("Obserwuj")
        self.sqlite_button.setEnabled(True)
        self.native_button.setEnabled(os.name == "nt")
        self.native_stream_button.setEnabled(os.name == "nt")
        self.import_button.setEnabled(True)

    def choose_state_database(self):
        if self.watch_worker is not None and self.watch_worker.isRunning():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Nowa lub istniejąca baza stanu Monitora", "monitor-state.sqlite",
            "SQLite (*.sqlite *.db)",
        )
        if not path:
            return
        try:
            self.set_state_database(path)
        except ValueError as error:
            QMessageBox.warning(self, "Nie wybrano bazy", str(error))

    def set_state_database(self, path):
        root = Path(self.folder.text()).resolve()
        destination = Path(path).resolve()
        if not root.is_dir() or destination.is_relative_to(root):
            raise ValueError("Baza SQLite musi być poza wybranym katalogiem.")
        if self.history_dirty or self.journal is not None:
            raise ValueError("Najpierw zapisz historię i wyłącz bieżący dziennik.")
        try:
            with WatchStateStore(root, destination) as store:
                events = store.load_events()
        except (OSError, sqlite3.Error) as error:
            raise ValueError(str(error)) from error
        self.state_path = str(destination)
        self.history["events"] = events
        self.render_history()
        self.sqlite_button.setText("SQLite wybrane")
        self.status.setText(f"Obserwacja będzie wznawiana z bazy: {destination}")

    def choose_legacy_import(self):
        if (self.history_dirty or self.journal is not None
                or (self.import_worker is not None and self.import_worker.isRunning())
                or (self.watch_worker is not None and self.watch_worker.isRunning())
                or (self.native_stream_worker is not None and self.native_stream_worker.isRunning())
                or (self.native_worker is not None and self.native_worker.isRunning())
                or (self.worker is not None and self.worker.isRunning())):
            QMessageBox.warning(self, "Nie rozpoczęto importu",
                                "Zatrzymaj obserwację oraz zapisz historię i wyłącz dziennik.")
            return
        source, _ = QFileDialog.getOpenFileName(self, "Stara baza Folder Watch", "", "SQLite (*.sqlite *.db)")
        if not source:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, "Nowa baza Monitora poza obserwowanym katalogiem", "monitor-import.sqlite",
            "SQLite (*.sqlite *.db)",
        )
        if not destination:
            return
        self.import_button.setEnabled(False)
        self.select_button.setEnabled(False)
        self.status.setText("Importuję starą bazę bez zmieniania źródła…")
        self.import_worker = LegacyImportWorker(source, self.folder.text(), destination, self)
        self.import_worker.loaded.connect(self.finish_legacy_import)
        self.import_worker.failed.connect(self.show_watch_error)
        self.import_worker.finished.connect(self.finish_legacy_import_worker)
        self.import_worker.start()

    def finish_legacy_import(self, result):
        try:
            self.set_state_database(result["destination"])
        except ValueError as error:
            self.status.setText(f"Import zakończony, ale nie wczytano bazy: {error}")
            return
        self.status.setText(
            f"Import zakończony: {result['files']} plików i {result['events']} zdarzeń. "
            "Czas wykonania starej migawki jest nieznany."
        )

    def finish_legacy_import_worker(self):
        self.import_button.setEnabled(True)
        self.select_button.setEnabled(True)

    def show_snapshot(self, snapshot):
        self.snapshot = snapshot
        files = snapshot["files"]
        comparison = None
        comparison_error = None
        if self.baseline is not None:
            try:
                comparison = compare_files(self.baseline, snapshot)
            except ValueError as error:
                comparison_error = str(error)
        removed = comparison.get("removed", []) if comparison and comparison["status"] == "COMPLETE" else []
        self.table.setRowCount(len(files) + len(removed))
        changed = set(comparison.get("changed", [])) if comparison and comparison["status"] == "COMPLETE" else set()
        added = set(comparison.get("added", [])) if comparison and comparison["status"] == "COMPLETE" else set()
        for index, row in enumerate(files):
            result = "Zmiana" if row["path"] in changed else "Nowy" if row["path"] in added else "Odczyt"
            for column, value in enumerate((row["path"], row["sha256"], result)):
                self.table.setItem(index, column, QTableWidgetItem(value))
        baseline_hashes = {row["path"]: row["sha256"] for row in self.baseline["files"]} if removed else {}
        for offset, path in enumerate(removed, start=len(files)):
            for column, value in enumerate((path, baseline_hashes[path], "Usunięty")):
                self.table.setItem(offset, column, QTableWidgetItem(value))
        self.save_button.setEnabled(snapshot["complete"])
        self.update_button.setEnabled(snapshot["complete"] and self.baseline_path is not None
                                      and comparison is not None and comparison["status"] == "COMPLETE")
        if not snapshot["complete"]:
            self.status.setText(f"UNKNOWN: {len(snapshot['errors'])} błędów lub pominięć; wynik niepełny.")
        elif comparison_error:
            self.status.setText(f"Nie porównano: {comparison_error}")
        elif comparison is not None and comparison["status"] == "COMPLETE":
            self.status.setText(
                f"Porównanie: {len(comparison['added'])} nowych, {len(comparison['removed'])} usuniętych, "
                f"{len(comparison['changed'])} zmienionych."
            )
        elif comparison is not None:
            self.status.setText("UNKNOWN: baseline lub bieżący skan jest niepełny.")
        else:
            self.status.setText(f"Odczytano {len(files)} plików. Wczytaj baseline, aby porównać.")

    def show_error(self, message):
        self.snapshot = None
        self.table.setRowCount(0)
        self.save_button.setEnabled(False)
        self.update_button.setEnabled(False)
        self.status.setText(f"Błąd skanu: {message}")

    def save_baseline(self):
        if self.snapshot is None or not self.snapshot["complete"]:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz baseline", "monitor-baseline.json", "JSON (*.json)")
        if not path:
            return
        try:
            save_snapshot(self.snapshot, path)
        except (FileExistsError, OSError) as error:
            QMessageBox.warning(self, "Nie zapisano baseline", str(error))
            return
        self.status.setText(f"Baseline zapisany: {path}")

    def load_baseline(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wczytaj baseline", "", "JSON (*.json)")
        if not path:
            return
        try:
            baseline = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(baseline, dict) and isinstance(baseline.get("files"), dict):
                converted = convert_baseline(baseline)
                new_path, _ = QFileDialog.getSaveFileName(
                    self, "Nowa kopia baseline dla Monitora (oryginał pozostanie)",
                    path + ".center.json", "JSON (*.json)")
                if not new_path:
                    return
                if Path(new_path).resolve().is_relative_to(Path(converted["root"]).resolve()):
                    raise ValueError("Nowy baseline musi być poza badanym katalogiem.")
                save_snapshot(converted, new_path)
                baseline = converted
                path = new_path
            if (not isinstance(baseline, dict) or baseline.get("schema_version") != 1
                    or not isinstance(baseline.get("root"), str)
                    or not isinstance(baseline.get("complete"), bool)
                    or not isinstance(baseline.get("files"), list)
                    or any(not isinstance(row, dict) or not isinstance(row.get("path"), str)
                           or not isinstance(row.get("sha256"), str) for row in baseline["files"])):
                raise ValueError("Nieobsługiwany format baseline.")
            self.baseline = baseline
            self.baseline_path = str(Path(path).resolve())
            self.extended_checkbox.setChecked(bool(baseline.get("options", {}).get("extended", False)))
            self.update_button.setEnabled(
                self.snapshot is not None and self.snapshot["complete"]
                and self.snapshot["root"] == baseline["root"] and baseline["complete"]
            )
        except (OSError, ValueError, TypeError, AttributeError) as error:
            QMessageBox.warning(self, "Nie wczytano baseline", str(error))
            return
        self.status.setText(f"Baseline wczytany: {path}. Uruchom skan tego samego katalogu.")

    def update_loaded_baseline(self):
        if self.baseline_path is None or self.snapshot is None or not self.snapshot["complete"]:
            return
        answer = QMessageBox.question(
            self, "Potwierdź aktualizację baseline",
            "Zastąpić wczytany baseline bieżącą migawką? Poprzednia wersja zostanie zapisana jako .bak.",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            result = update_baseline(self.baseline_path, self.snapshot, accept_changes=True)
        except (OSError, ValueError, KeyError, TypeError) as error:
            QMessageBox.warning(self, "Nie zaktualizowano baseline", str(error))
            return
        self.baseline = self.snapshot
        self.status.setText(f"Baseline zaktualizowany. Poprzednia wersja: {result['backup']}")

    def generate_signing_keys(self):
        private, _ = QFileDialog.getSaveFileName(self, "Nowy klucz prywatny", "prestige-private.pem", "PEM (*.pem)")
        if not private:
            return
        public = str(Path(private).with_name(Path(private).stem + "-public.pem"))
        password, ok = QInputDialog.getText(self, "Hasło klucza", "Hasło (minimum 12 bajtów):", QLineEdit.Password)
        if not ok:
            return
        repeat, ok = QInputDialog.getText(self, "Potwierdź hasło", "Powtórz hasło:", QLineEdit.Password)
        if not ok:
            return
        if password != repeat:
            QMessageBox.warning(self, "Klucze", "Hasła są różne.")
            return
        try:
            new_key(private, public, password)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie utworzono kluczy", str(error))
            return
        self.status.setText(f"Klucze utworzone. Klucz publiczny: {public}")

    def sign_baseline(self):
        if not self.baseline_path:
            QMessageBox.information(self, "Podpis", "Najpierw wczytaj lub zapisz baseline i wczytaj ten plik.")
            return
        private, _ = QFileDialog.getOpenFileName(self, "Klucz prywatny", "", "PEM (*.pem)")
        if not private:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Nowy plik podpisu", self.baseline_path + ".sig.json", "JSON (*.json)")
        if not destination:
            return
        password, ok = QInputDialog.getText(self, "Hasło klucza", "Hasło:", QLineEdit.Password)
        if not ok:
            return
        try:
            sign(self.baseline_path, private, destination, password)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie podpisano baseline", str(error))
            return
        self.status.setText(f"Podpis zapisany: {destination}")

    def verify_baseline_signature(self):
        if not self.baseline_path:
            QMessageBox.information(self, "Podpis", "Najpierw wczytaj baseline.")
            return
        public, _ = QFileDialog.getOpenFileName(self, "Zaufany klucz publiczny", "", "PEM (*.pem)")
        if not public:
            return
        signature, _ = QFileDialog.getOpenFileName(self, "Plik podpisu", self.baseline_path + ".sig.json", "JSON (*.json)")
        if not signature:
            return
        try:
            result = verify(self.baseline_path, public, signature)
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie sprawdzono podpisu", str(error))
            return
        self.status.setText("Podpis poprawny względem podanego klucza." if result["ok"] else result["reason"])

    def show_help(self):
        QMessageBox.information(
            self, "Pomoc — Monitor",
            "Skan nie zmienia plików. Opcja ACL/ADS dołącza uprawnienia i alternatywne strumienie; "
            "Podpis Ed25519 wymaga zaufanego klucza publicznego; klucz prywatny jest szyfrowany hasłem. "
            "Karta Hash Checker obsługuje plik, manifest folderu i jego odłączony podpis; SHA-1/MD5 są tylko do zgodności, "
            "a niepełny skan nie jest zapisywany jako baseline. Weryfikacja integralności "
            "wymaga skanu w tym samym trybie co baseline. Baseline zapisuje ścieżki i hashe SHA-256 w wybranym nowym pliku. "
            "Aktualizacja wczytanego baseline wymaga potwierdzenia i tworzy kopię .bak. "
            "Przy błędzie odczytu wynik jest UNKNOWN. Nie skanuj folderu z baseline, jeśli nie chcesz, "
            "aby sam plik baseline pojawił się jako nowy plik. Historię możesz zapisać ręcznie albo "
            "włączyć automatyczny dziennik JSONL poza obserwowanym katalogiem. "
            "Baza SQLite poza katalogiem zachowuje ostatnią migawkę i zdarzenia; "
            "po wznowieniu pokazuje zmiany od poprzedniego uruchomienia. "
            "Import starej bazy tworzy nowy plik SQLite bez zmieniania starego; "
            "czas wykonania starej migawki jest nieznany. "
            "Przycisk Natywne 10 s zbiera zdarzenia FileSystemWatcher przez 10 sekund; "
            "Natywnie: start prowadzi ciągły odczyt w jednym procesie aż do zatrzymania; "
            "zapisz historię ręcznie lub włącz dziennik JSONL. SQLite utrwala stan trybu polling. "
            "Windows może zgłosić kilka zdarzeń dla jednej zmiany. Przepełnienie bufora oznacza UNKNOWN. "
            "Opcja ACL/ADS obejmuje też obserwację polling i wymaga zgodnego trybu zapisanej bazy SQLite; "
            "może znacząco spowolnić każdy odczyt. Obserwacja sprawdza zmiany co 2 sekundy i co 30 odczytów hashuje ponownie "
            "wszystkie pliki. Zmiana ukryta przez identyczny rozmiar i czas modyfikacji "
            "może zostać wykryta dopiero podczas pełnego hashowania."
        )

    def choose_hash_file(self):
        if self.hash_worker is not None and self.hash_worker.isRunning():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Plik do hashowania")
        if not path:
            return
        self.hash_button.setEnabled(False)
        self.hash_result.setPlainText("Hashuję plik…")
        self.hash_worker = HashWorker(path, self.hash_algorithm.currentText(), self)
        self.hash_worker.loaded.connect(self.show_hash_result)
        self.hash_worker.failed.connect(self.show_hash_error)
        self.hash_worker.finished.connect(lambda: self.hash_button.setEnabled(True))
        self.hash_worker.start()

    def show_hash_result(self, hashes):
        algorithm, value = next(iter(hashes.items()))
        expected = self.hash_expected.text().strip().lower()
        comparison = "ZGODNY" if expected == value else "NIEZGODNY" if expected else "bez wartości porównawczej"
        self.hash_result.setPlainText(f"{algorithm.upper()}: {value}\nPorównanie: {comparison}")

    def show_hash_error(self, message):
        self.hash_result.setPlainText(f"Nie obliczono hashu: {message}")

    def choose_manifest_generate(self):
        if self.manifest_worker is not None and self.manifest_worker.isRunning():
            return
        root = QFileDialog.getExistingDirectory(self, "Folder do manifestu")
        if not root:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Nowy manifest poza folderem", "hash-manifest.json", "JSON (*.json)")
        if not destination:
            return
        self.start_manifest_worker(root, self.hash_algorithm.currentText(), destination=destination)

    def choose_manifest_verify(self):
        if self.manifest_worker is not None and self.manifest_worker.isRunning():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Manifest do sprawdzenia", "", "JSON (*.json)")
        if not path:
            return
        root = QFileDialog.getExistingDirectory(self, "Folder do porównania z manifestem")
        if not root:
            return
        try:
            baseline = compatible_manifest(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError) as error:
            self.hash_result.setPlainText(f"Nie wczytano manifestu: {error}")
            return
        self.start_manifest_worker(root, baseline["algorithm"], baseline=baseline)

    def choose_compare_folders(self):
        if self.manifest_worker is not None and self.manifest_worker.isRunning():
            return
        left = QFileDialog.getExistingDirectory(self, "Pierwszy folder do porównania")
        if not left:
            return
        right = QFileDialog.getExistingDirectory(self, "Drugi folder do porównania")
        if right:
            self.start_manifest_worker(left, self.hash_algorithm.currentText(), other=right)

    def choose_compare_manifests(self):
        left, _ = QFileDialog.getOpenFileName(self, "Pierwszy manifest", "", "JSON (*.json)")
        if not left:
            return
        right, _ = QFileDialog.getOpenFileName(self, "Drugi manifest", "", "JSON (*.json)")
        if not right:
            return
        try:
            before = compatible_manifest(json.loads(Path(left).read_text(encoding="utf-8")))
            after = compatible_manifest(json.loads(Path(right).read_text(encoding="utf-8")))
            self.show_manifest_result({"mode": "verified", "result": compare_manifests(before, after)})
        except (OSError, ValueError, TypeError, KeyError) as error:
            self.show_hash_error(str(error))

    def sign_manifest(self):
        manifest, _ = QFileDialog.getOpenFileName(self, "Manifest do podpisania", "", "JSON (*.json)")
        if not manifest:
            return
        try:
            data = validate_manifest(json.loads(Path(manifest).read_text(encoding="utf-8")))
            if not data["complete"]:
                raise ValueError("Nie podpisuj niepełnego manifestu jako potwierdzonego skanu.")
        except (OSError, ValueError, TypeError) as error:
            self.hash_result.setPlainText(f"Nie podpisano manifestu: {error}")
            return
        private, _ = QFileDialog.getOpenFileName(self, "Klucz prywatny", "", "PEM (*.pem)")
        if not private:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Nowy podpis manifestu", manifest + ".sig.json", "JSON (*.json)")
        if not destination:
            return
        password, ok = QInputDialog.getText(self, "Hasło klucza", "Hasło:", QLineEdit.Password)
        if not ok:
            return
        try:
            sign(manifest, private, destination, password)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            self.hash_result.setPlainText(f"Nie podpisano manifestu: {error}")
            return
        self.hash_result.setPlainText(f"Podpis manifestu zapisany: {destination}")

    def verify_manifest_signature(self):
        manifest, _ = QFileDialog.getOpenFileName(self, "Manifest do sprawdzenia", "", "JSON (*.json)")
        if not manifest:
            return
        try:
            validate_manifest(json.loads(Path(manifest).read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError) as error:
            self.hash_result.setPlainText(f"Nieprawidłowy manifest: {error}")
            return
        public, _ = QFileDialog.getOpenFileName(self, "Zaufany klucz publiczny", "", "PEM (*.pem)")
        if not public:
            return
        signature, _ = QFileDialog.getOpenFileName(self, "Podpis manifestu", manifest + ".sig.json", "JSON (*.json)")
        if not signature:
            return
        try:
            result = verify(manifest, public, signature)
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
            self.hash_result.setPlainText(f"Nie sprawdzono podpisu: {error}")
            return
        self.hash_result.setPlainText(
            "Podpis manifestu poprawny względem podanego klucza; tożsamość właściciela klucza nie jest potwierdzona."
            if result["ok"] else f"Podpis manifestu niepoprawny: {result['reason']}")

    def start_manifest_worker(self, root, algorithm, *, destination=None, baseline=None,
                              other=None):
        self.manifest_save_button.setEnabled(False)
        self.manifest_verify_button.setEnabled(False)
        self.compare_folders_button.setEnabled(False)
        self.compare_manifests_button.setEnabled(False)
        self.manifest_cancel_button.setEnabled(True)
        self.hash_result.setPlainText("Skanuję folder…")
        self.manifest_worker = ManifestWorker(root, algorithm, destination, baseline,
                                              other, self)
        self.manifest_worker.loaded.connect(self.show_manifest_result)
        self.manifest_worker.failed.connect(self.show_hash_error)
        self.manifest_worker.finished.connect(self.finish_manifest)
        self.manifest_worker.start()

    def show_manifest_result(self, result):
        if result["mode"] == "saved":
            self.hash_result.setPlainText(f"Manifest zapisany: {result['path']}\nPlików: {result['count']}")
        else:
            comparison = result["result"]
            if comparison["status"] != "COMPLETE":
                self.hash_result.setPlainText(f"UNKNOWN: {comparison['reason']}")
            else:
                self.hash_result.setPlainText(
                    f"Zgodność: {'TAK' if comparison['ok'] else 'NIE'}\n"
                    f"Nowe: {comparison['new']}\nBrakujące: {comparison['missing']}\n"
                    f"Zmienione: {comparison['changed']}"
                )

    def cancel_manifest(self):
        if self.manifest_worker is not None and self.manifest_worker.isRunning():
            self.manifest_worker.cancel_event.set()

    def finish_manifest(self):
        self.manifest_save_button.setEnabled(True)
        self.manifest_verify_button.setEnabled(True)
        self.compare_folders_button.setEnabled(True)
        self.compare_manifests_button.setEnabled(True)
        self.manifest_cancel_button.setEnabled(False)

    def closeEvent(self, event):
        if self.hash_worker is not None and self.hash_worker.isRunning():
            self.hash_worker.wait()
        if self.manifest_worker is not None and self.manifest_worker.isRunning():
            self.manifest_worker.cancel_event.set()
            self.manifest_worker.wait()
        if self.import_worker is not None and self.import_worker.isRunning():
            self.import_worker.wait()
        if self.native_stream_worker is not None and self.native_stream_worker.isRunning():
            self.native_stream_worker.stop()
            self.native_stream_worker.wait()
        if self.native_worker is not None and self.native_worker.isRunning():
            self.native_worker.wait()
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel_event.set()
            self.worker.wait()
        if self.watch_worker is not None and self.watch_worker.isRunning():
            self.watch_worker.stop_event.set()
            self.watch_worker.wait()
        if self.journal is not None:
            self.journal.close()
        super().closeEvent(event)
