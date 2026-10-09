"""Katalog dokumentowanych odczytów rejestru bez operacji zapisu."""

from pathlib import Path
from datetime import datetime
from threading import Event

from PySide6.QtCore import QSettings, QThread, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
    QLineEdit, QFileDialog, QComboBox, QCheckBox, QScrollArea, QGridLayout, QSizePolicy,
)

from prestige_core.registry_read import OPERATIONS, read_operation
from prestige_core.registry_admx import load_admx_catalog
from prestige_core.registry_audit import audit_catalog
from prestige_core.report_live import summarize_live_result
from prestige_core.registry_change import rollback_file_extensions, show_file_extensions
from prestige_core.registry_guides import GUIDES, completion_instructions
from prestige_core.registry_backup_store import list_backups, new_backup_path, default_backup_dir
from prestige_core.registry_policy_changes import (
    OPERATIONS as POLICY_OPERATIONS, apply_policy_change, plan_policy_change,
    preview_policy_rollback, rollback_policy_change,
)
from prestige_core.offline_license import verify_license
from prestige_core.registry_transactions import (OPERATIONS as CHANGE_OPERATIONS,
                                                  apply_change, export_change_diff, plan_change, preview_rollback_change,
                                                  rollback_change)
from prestige_core.ui_theme import APP_QSS, COLORS
from prestige_report.gui import ReportDialog


class RegistryWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, operation, catalog, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.catalog = catalog

    def run(self):
        try:
            self.loaded.emit(read_operation(self.operation, catalog=self.catalog))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class RegistryAuditWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)
    progress = Signal(int, int)

    def __init__(self, catalog, parent=None):
        super().__init__(parent)
        self.catalog = tuple(catalog)
        self.cancel_event = Event()

    def run(self):
        try:
            self.loaded.emit(audit_catalog(self.catalog, cancel_event=self.cancel_event,
                                           on_progress=self.progress.emit))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class RegistryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PRESTIGE TECH — Registry Manager")
        self.resize(1120, 720)
        self.setMinimumSize(820, 560)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        self.audit_worker = None
        self.last_audit = None
        self.report_dialog = None
        self.catalog = list(OPERATIONS)
        self.edition = "FREE"
        self.preferences = QSettings("PrestigeTech", "RegistryManager")
        public_key_path = Path(__file__).resolve().parent.parent / "prestige_core" / "assets" / "pro-public.pem"
        self.pro_public_key = public_key_path.read_bytes() if public_key_path.is_file() else None
        if self.pro_public_key is not None:
            saved_license = self.preferences.value("pro_license_file", "", type=str)
            if saved_license:
                try:
                    self.license_info = verify_license(saved_license, self.pro_public_key)
                    self.edition = "PRO"
                except (OSError, ValueError, RuntimeError):
                    self.preferences.remove("pro_license_file")
        self.visible_operations = list(self.catalog)
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
        side.addWidget(QLabel("REGISTRY MANAGER"))
        side.addSpacing(28)
        side.addWidget(QLabel("● Bezpieczny odczyt"))
        side.addStretch()
        side.addWidget(QLabel("By Dominik Wasilak"))
        layout.addWidget(sidebar)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 22, 24, 22)
        title = QLabel("Rejestr Windows")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        main.addWidget(title)
        catalog_summary = QLabel(f"{len(OPERATIONS)} odczytów ręcznych; ADMX może rozszerzyć katalog. "
                                 f"{len(CHANGE_OPERATIONS) + len(POLICY_OPERATIONS) + 1} zmian HKCU z kopią (testy fixture).")
        catalog_summary.setWordWrap(True)
        main.addWidget(catalog_summary)
        self.edition_label = QLabel("Wersja FREE — podstawowe funkcje" if self.edition == "FREE"
                                    else f"Wersja PRO — ważna do {self.license_info['expires']}")
        main.addWidget(self.edition_label)
        self.activate_button = QPushButton("Aktywuj klucz PRO offline")
        self.activate_button.clicked.connect(self.activate_pro)
        main.addWidget(self.activate_button)
        self.admx_button = QPushButton("Dodaj odczyty ADMX")
        self.admx_button.setToolTip("Odczytaj opis zasad z lokalnych szablonów Windows; bez zmiany rejestru.")
        self.admx_button.clicked.connect(self.load_admx)
        main.addWidget(self.admx_button)
        audit_actions = QGridLayout()
        self.audit_button = QPushButton("Audyt katalogu")
        self.audit_button.setToolTip("Odczytaj wszystkie pozycje katalogu bez zmiany wartości rejestru.")
        self.audit_button.clicked.connect(self.toggle_audit)
        audit_actions.addWidget(self.audit_button, 0, 0)
        self.report_button = QPushButton("Ostatni audyt → Repair Report")
        self.report_button.setEnabled(False)
        self.report_button.clicked.connect(self.open_audit_report)
        audit_actions.addWidget(self.report_button, 1, 0)
        main.addLayout(audit_actions)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Szukaj po ID, nazwie lub kategorii")
        self.search.textChanged.connect(self.filter_operations)
        main.addWidget(self.search)
        self.operations = QListWidget()
        self.operations.setMinimumHeight(100)
        self.operations.setMaximumHeight(140)
        for operation in OPERATIONS:
            self.operations.addItem(f"{operation.id}  {operation.name}")
        self.operations.currentRowChanged.connect(self.show_operation)
        main.addWidget(self.operations)
        self.description = QLabel("Wybierz operację.")
        self.description.setWordWrap(True)
        main.addWidget(self.description)
        actions = QHBoxLayout()
        self.read_button = QPushButton("Odczytaj")
        self.read_button.setEnabled(False)
        self.read_button.clicked.connect(self.start_read)
        actions.addWidget(self.read_button)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        actions.addWidget(self.help_button)
        main.addLayout(actions)
        change_actions = QGridLayout()
        self.extensions_button = QPushButton("Pokaż rozszerzenia plików (z kopią)")
        self.extensions_button.setToolTip(GUIDES["REG-WRITE-001"].summary + " " +
                                          GUIDES["REG-WRITE-001"].impact)
        self.extensions_button.clicked.connect(self.apply_extensions_change)
        change_actions.addWidget(self.extensions_button, 0, 0)
        self.rollback_button = QPushButton("Cofnij zmianę z kopii")
        self.rollback_button.clicked.connect(self.rollback_extensions_change)
        change_actions.addWidget(self.rollback_button, 1, 0)
        main.addLayout(change_actions)
        additional_actions = QGridLayout()
        self.change_choice = QComboBox()
        self.change_choice.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.change_choice.setMinimumContentsLength(16)
        self.change_choice.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        for item in CHANGE_OPERATIONS:
            guide = GUIDES[item.id]
            self.change_choice.addItem(f"{guide.level} · {guide.edition} · {item.label}", item.id)
        self.change_choice.currentIndexChanged.connect(self.show_change_guide)
        main.addWidget(self.change_choice)
        self.change_plan_button = QPushButton("Plan")
        self.change_plan_button.clicked.connect(self.plan_selected_change)
        additional_actions.addWidget(self.change_plan_button, 0, 0)
        self.change_apply_button = QPushButton("Zmień z kopią")
        self.change_apply_button.clicked.connect(self.apply_selected_change)
        additional_actions.addWidget(self.change_apply_button, 0, 1)
        self.change_rollback_button = QPushButton("Cofnij z kopii")
        self.change_rollback_button.clicked.connect(self.rollback_selected_change)
        additional_actions.addWidget(self.change_rollback_button, 1, 0)
        diff_button = QPushButton("Eksport różnicy")
        diff_button.clicked.connect(self.export_selected_diff)
        additional_actions.addWidget(diff_button, 1, 1)
        main.addLayout(additional_actions)
        self.change_guide = QLabel("")
        self.change_guide.setWordWrap(True)
        main.addWidget(self.change_guide)
        self.show_change_guide()
        policy_actions = QGridLayout()
        self.policy_choice = QComboBox()
        self.policy_choice.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.policy_choice.setMinimumContentsLength(16)
        self.policy_choice.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        for item in POLICY_OPERATIONS:
            guide = GUIDES[item.id]
            self.policy_choice.addItem(f"{guide.level} · {guide.edition} · {item.label}", item.id)
        main.addWidget(self.policy_choice)
        self.policy_plan_button = QPushButton("Plan polityki")
        self.policy_plan_button.clicked.connect(self.plan_selected_policy)
        policy_actions.addWidget(self.policy_plan_button, 0, 0)
        self.policy_apply_button = QPushButton("Zmień politykę")
        self.policy_apply_button.clicked.connect(self.apply_selected_policy)
        policy_actions.addWidget(self.policy_apply_button, 0, 1)
        self.policy_rollback_button = QPushButton("Cofnij politykę")
        self.policy_rollback_button.clicked.connect(self.rollback_selected_policy)
        policy_actions.addWidget(self.policy_rollback_button, 1, 0, 1, 2)
        main.addLayout(policy_actions)
        self.experimental_policies = QCheckBox("Tryb eksperymentalny")
        self.experimental_policies.setToolTip(
            "Domyślnie wyłączony. Zachowanie polityk na tej edycji nie jest potwierdzone przez Microsoft. "
            "Każda zmiana nadal wymaga nowej kopii i osobnego potwierdzenia.")
        main.addWidget(self.experimental_policies)
        self.policy_guide = QLabel("")
        self.policy_guide.setWordWrap(True)
        main.addWidget(self.policy_guide)
        self.policy_choice.currentIndexChanged.connect(self.show_policy_guide)
        self.show_policy_guide()
        backups_title = QLabel("Moje kopie zmian")
        backups_title.setStyleSheet("font-size: 14pt; font-weight: 700;")
        main.addWidget(backups_title)
        self.backups_choice = QComboBox()
        self.backups_choice.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.backups_choice.setMinimumContentsLength(16)
        self.backups_choice.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.backups_choice.currentIndexChanged.connect(self.show_backup_choice)
        main.addWidget(self.backups_choice)
        backup_actions = QGridLayout()
        self.refresh_backups_button = QPushButton("Odśwież kopie")
        self.refresh_backups_button.clicked.connect(self.refresh_backups)
        backup_actions.addWidget(self.refresh_backups_button, 0, 0)
        self.managed_rollback_button = QPushButton("Cofnij wybraną zmianę")
        self.managed_rollback_button.clicked.connect(self.rollback_managed_backup)
        backup_actions.addWidget(self.managed_rollback_button, 0, 1)
        main.addLayout(backup_actions)
        self.backup_note = QLabel("")
        self.backup_note.setWordWrap(True)
        main.addWidget(self.backup_note)
        self.refresh_backups()
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.table = QTableWidget(0, 4)
        self.table.setMinimumHeight(170)
        self.table.setHorizontalHeaderLabels(["Wartość", "Dane", "Typ", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        card_layout.addWidget(self.table)
        main.addWidget(card, 2)
        self.status = QLabel("Brak odczytu.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        self.change_summary = QLabel("")
        self.change_summary.setWordWrap(True)
        self.change_summary.setObjectName("ChangeSummary")
        self.change_summary.setStyleSheet(
            "QLabel#ChangeSummary{background:#08293b;border:1px solid #2386af;"
            "border-radius:10px;padding:12px;color:#f1f8fc;}"
        )
        self.change_summary.hide()
        main.addWidget(self.change_summary)
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setWidget(content)
        layout.addWidget(self.content_scroll, 1)

    def filter_operations(self, query):
        needle = query.casefold().strip()
        self.visible_operations = [operation for operation in self.catalog if needle in
                                   f"{operation.id} {operation.name} {operation.category}".casefold()]
        self.operations.clear()
        for operation in self.visible_operations:
            self.operations.addItem(f"{operation.id}  {operation.name}")
        self.description.setText("Wybierz operację.")
        self.read_button.setEnabled(False)
        self.table.setRowCount(0)

    def show_operation(self, index):
        self.table.setRowCount(0)
        if not 0 <= index < len(self.visible_operations):
            self.read_button.setEnabled(False)
            return
        operation = self.visible_operations[index]
        self.description.setText(
            f"{operation.category}: {operation.purpose}\n"
            f"{operation.hive}\\{operation.key}\nŹródło: {operation.source}"
        )
        self.read_button.setEnabled(True)
        self.status.setText("Wybierz Odczytaj. Operacja nie zapisuje zmian.")

    def start_read(self):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        if self.worker is not None and self.worker.isRunning():
            return
        index = self.operations.currentRow()
        if not 0 <= index < len(self.visible_operations):
            return
        self.read_button.setEnabled(False)
        self.search.setEnabled(False)
        self.table.setRowCount(0)
        self.status.setText("Odczytuję rejestr…")
        self.worker = RegistryWorker(self.visible_operations[index], tuple(self.catalog), self)
        self.worker.loaded.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.finish_read)
        self.worker.start()

    def finish_read(self):
        self.search.setEnabled(True)
        self.read_button.setEnabled(0 <= self.operations.currentRow() < len(self.visible_operations))

    def show_result(self, result):
        rows = result["rows"]
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, value in enumerate((row["name"], row["value"] if row["value"] is not None else
                                            "Nie ustawiono", str(row["type"] or "—"),
                                            "Nie ustawiono" if row["status"] == "Niedostępne" else row["status"])):
                self.table.setItem(index, column, QTableWidgetItem(value))
        self.status.setText(f"{result['status']}: {result['reason'] or f'Odczytano {len(rows)} wartości.'}")

    def show_error(self, message):
        self.table.setRowCount(0)
        self.status.setText(f"Nie udało się odczytać: {message}")

    def activate_pro(self):
        if self.pro_public_key is None:
            self.status.setText("Klucz publiczny wydawcy nie jest jeszcze skonfigurowany w tym wydaniu.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Podpisany klucz PRO", "", "JSON (*.json)")
        if not path:
            return
        try:
            result = verify_license(path, self.pro_public_key)
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText("Nie aktywowano PRO: " + str(error))
            return
        self.edition = "PRO"
        self.license_info = result
        self.preferences.setValue("pro_license_file", path)
        self.edition_label.setText(f"Wersja PRO — ważna do {result['expires']}")
        self.show_change_guide()
        self.show_policy_guide()

    def pro_active(self):
        path = self.preferences.value("pro_license_file", "", type=str)
        if not path or self.pro_public_key is None:
            return False
        try:
            verify_license(path, self.pro_public_key)
            return True
        except (OSError, ValueError, RuntimeError):
            self.preferences.remove("pro_license_file")
            self.edition = "FREE"
            self.edition_label.setText("Wersja FREE — podstawowe funkcje")
            return False

    def show_change_guide(self):
        guide = GUIDES.get(self.change_choice.currentData())
        if guide is None:
            return
        self.change_guide.setText(
            f"{guide.level} · {guide.edition} — {guide.summary}\n"
            f"Co się zmieni: {guide.impact} Po zmianie: {guide.after} "
            "Przed wykonaniem powstaje plan i kopia; możesz ją później wskazać do cofnięcia.")
        self.change_apply_button.setEnabled(guide.edition == "FREE" or self.edition == "PRO")

    def show_policy_guide(self):
        guide = GUIDES.get(self.policy_choice.currentData())
        if guide is None:
            return
        self.policy_guide.setText(f"{guide.level} · {guide.edition} — {guide.summary}\n"
                                  f"Skutek: {guide.impact} Po zmianie: {guide.after}")
        self.policy_apply_button.setEnabled(guide.edition == "FREE" or self.edition == "PRO")

    def refresh_backups(self):
        self.backups_choice.clear()
        try:
            rows = list_backups()
        except (OSError, ValueError) as error:
            self.backup_note.setText(f"Nie można odczytać listy kopii: {error}")
            self.managed_rollback_button.setEnabled(False)
            return
        for item in rows:
            when = datetime.fromisoformat(item["modified_utc"]).astimezone().strftime("%Y-%m-%d %H:%M")
            status_label = {
                "APPLIED": "można cofnąć", "APPLIED_OR_UNKNOWN": "stan do sprawdzenia",
                "ROLLED_BACK": "cofnięto", "PREPARED": "operacja przerwana",
                "ABORTED_CONFLICT": "inny program zmienił ustawienie",
                "RECOVERY_NEEDED": "wymaga ręcznej kontroli",
            }[item["status"]]
            self.backups_choice.addItem(f"{when} · {item['label']} · {status_label}", item)
        self.show_backup_choice()

    def show_backup_choice(self):
        item = self.backups_choice.currentData()
        if not item:
            self.backup_note.setText("Brak zapisanych kopii zmian. Program zapisze je automatycznie przed zmianą.")
            self.managed_rollback_button.setEnabled(False)
            return
        if item["status"] in ("PREPARED", "RECOVERY_NEEDED", "ABORTED_CONFLICT"):
            self.backup_note.setText(
                "Ta operacja nie ma potwierdzonego końcowego stanu. Nie cofaj jej automatycznie; "
                f"zachowaj kopię z {default_backup_dir()} do ręcznej kontroli.")
        elif item["status"] == "ROLLED_BACK":
            self.backup_note.setText("To ustawienie zostało już cofnięte.")
        else:
            self.backup_note.setText(
                f"{GUIDES[item['operation']].summary} Kopia w: {default_backup_dir()}. "
                "Cofnięcie sprawdzi, czy ustawienie nie zmieniło się później.")
        self.managed_rollback_button.setEnabled(item["status"] in
                                                ("APPLIED", "APPLIED_OR_UNKNOWN"))

    def rollback_managed_backup(self):
        item = self.backups_choice.currentData()
        if not item or not self.managed_rollback_button.isEnabled():
            return
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        try:
            if item["kind"] == "change":
                preview = preview_rollback_change(item["path"])
            elif item["kind"] == "policy":
                preview = preview_policy_rollback(item["path"])
            else:
                preview = None
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(f"Nie można przygotować cofnięcia: {error}")
            return
        if preview is not None and preview["status"] != "PLAN":
            self.status.setText("Ustawienie zmieniło się od zapisu kopii. Niczego nie nadpisano.")
            return
        answer = QMessageBox.question(self, "Cofnij ostatnią zmianę",
                                      f"Przywrócić poprzednie ustawienie?\n{GUIDES[item['operation']].summary}\n"
                                      "Program odmówi, jeśli wartość zmieniono później.",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            if item["kind"] == "change":
                result = rollback_change(item["path"], accept_changes=True)
            elif item["kind"] == "policy":
                result = rollback_policy_change(item["path"], accept_changes=True)
            else:
                result = rollback_file_extensions(item["path"], accept_changes=True)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie cofnięto zmiany", str(error))
            return
        self.status.setText(f"{result['status']}: poprzednie ustawienie przywrócone.")
        self.change_summary.setText(completion_instructions(item["operation"], item["path"], undone=True))
        self.change_summary.show()
        self.refresh_backups()

    def show_help(self):
        QMessageBox.information(
            self, "Pomoc — Registry Manager",
            f"Ten etap ma {len(OPERATIONS)} ręcznie skatalogowanych operacji odczytu; "
            "może dodać osobne odczyty z lokalnych szablonów ADMX Microsoftu. "
            f"{len(CHANGE_OPERATIONS) + len(POLICY_OPERATIONS) + 1} wąskich zmian HKCU sprawdzonych na atrapach. "
            "Każda zmiana wymaga potwierdzenia i nowej kopii JSON; cofanie odmawia nadpisania wartości zmienionej później. "
            "Opis przy każdej zmianie wyjaśnia efekt i krok sprawdzenia bez znajomości rejestru. "
            "Brak wartości lub uprawnień pokazuje jako Niedostępne. "
            "Cel to 600 odrębnych zmian; odczyty ADMX nie są zmianami."
        )

    def load_admx(self):
        if ((self.worker is not None and self.worker.isRunning()) or
                (self.audit_worker is not None and self.audit_worker.isRunning())):
            return
        try:
            result = load_admx_catalog(r"C:\Windows\PolicyDefinitions")
        except (OSError, ValueError) as error:
            self.status.setText(f"Nie wczytano ADMX: {error}")
            return
        self.catalog = list(OPERATIONS) + list(result["operations"])
        self.filter_operations(self.search.text())
        self.status.setText(f"ADMX: {len(result['operations'])} odrębnych zasad z "
                            f"{result['templates']} szablonów; łącznie {len(self.catalog)} odczytów; "
                            f"{len(result['errors'])} błędów. "
                            "Nieustawiona zasada będzie oznaczona Niedostępne.")

    def toggle_audit(self):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.audit_worker.cancel_event.set()
            self.status.setText("Przerywam audyt po bieżącym odczycie…")
            return
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Poczekaj na zakończenie pojedynczego odczytu.")
            return
        self.audit_button.setText("Przerwij audyt")
        self.last_audit = None
        self.report_button.setEnabled(False)
        self.admx_button.setEnabled(False)
        self.status.setText(f"Odczytuję {len(self.catalog)} operacji bez zapisywania wartości…")
        self.audit_worker = RegistryAuditWorker(self.catalog, self)
        self.audit_worker.progress.connect(
            lambda done, total: self.status.setText(f"Audyt Registry: {done}/{total} odczytów…"))
        self.audit_worker.loaded.connect(self.show_audit_result)
        self.audit_worker.failed.connect(lambda message: self.status.setText(f"Audyt niedostępny: {message}"))
        self.audit_worker.finished.connect(self.finish_audit)
        self.audit_worker.start()

    def show_audit_result(self, result):
        self.last_audit = result
        self.report_button.setEnabled(True)
        counts = result["counts"]
        details = result.get("details", {})
        not_set = details.get("KEY_NOT_FOUND", 0) + details.get("VALUE_NOT_SET", 0) + details.get("NOT_SET", 0)
        self.status.setText(f"{result['status']}: {result['processed']}/{result['total']}; "
                            f"odczytane {counts.get('OK', 0)}, nieustawione {not_set}, "
                            f"odmowa dostępu {details.get('ACCESS_DENIED', 0)}, "
                            f"błędy {counts.get('ERROR', 0)}. "
                            "Wartości nie zostały zapisane.")

    def open_audit_report(self):
        if self.last_audit is None:
            return
        try:
            prefill = summarize_live_result("Registry", self.last_audit)
        except ValueError as error:
            self.status.setText("Nie przekazano audytu do raportu: " + str(error))
            return
        self.report_dialog = ReportDialog(self, prefill=prefill)
        self.report_dialog.show()

    def finish_audit(self):
        self.audit_button.setText("Audyt katalogu")
        self.admx_button.setEnabled(True)

    def apply_extensions_change(self):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        answer = QMessageBox.question(
            self, "Zmiana widoku Eksploratora",
            "Pokazać końcówki nazw plików, np. .pdf i .exe?\n"
            "Łatwiej będzie rozpoznać typ pliku. Zawartość plików się nie zmieni.\n"
            "Najpierw zapiszę kopię ustawienia do nowego pliku JSON.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            backup = new_backup_path("REG-WRITE-001")
            result = show_file_extensions(backup, accept_changes=True)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie zmieniono rejestru", str(error))
            return
        self.refresh_backups()
        self.status.setText("Rozszerzenia są już widoczne." if result["status"] == "ALREADY_SET"
                            else f"Zmiana zweryfikowana. Kopia: {result['backup']}")
        if result["status"] == "APPLIED":
            self.change_summary.setText(completion_instructions("REG-WRITE-001", result["backup"]))
            self.change_summary.show()

    def rollback_extensions_change(self):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        backup, _ = QFileDialog.getOpenFileName(self, "Kopia HideFileExt", "", "JSON (*.json)")
        if not backup:
            return
        answer = QMessageBox.question(self, "Cofnij zmianę",
                                      "Przywrócić poprzedni sposób pokazywania końcówek nazw plików?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            rollback_file_extensions(backup, accept_changes=True)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie cofnięto zmiany", str(error))
            return
        self.status.setText("Poprzednia wartość HideFileExt została przywrócona i zweryfikowana.")

    def plan_selected_change(self):
        try:
            plan = plan_change(self.change_choice.currentData())
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(f"Plan niedostępny: {error}")
            return
        self.status.setText(f"{plan['operation']}: {plan['name']} {plan['current']} → "
                            f"{plan['target']}. {'Wymaga zmiany' if plan['change_needed'] else 'Już ustawione'}.")

    def plan_selected_policy(self):
        try:
            plan = plan_policy_change(self.policy_choice.currentData(),
                                      allow_unsupported=self.experimental_policies.isChecked())
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(f"Plan polityki niedostępny: {error}")
            return
        before = "brak wartości" if plan["current"] is None else str(plan["current"])
        self.status.setText(f"{plan['operation']}: {before} → {plan['target']}; "
                            f"{'wymaga zmiany' if plan['change_needed'] else 'już ustawione'}. "
                            + ("TRYB EKSPERYMENTALNY — skutku nie potwierdzono na tej edycji."
                               if not plan['supported_edition'] else ""))

    def apply_selected_policy(self):
        operation_id = self.policy_choice.currentData()
        guide = GUIDES[operation_id]
        if guide.edition == "PRO" and not self.pro_active():
            self.status.setText("Ta zmiana wymaga podpisanej licencji PRO.")
            return
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        try:
            plan = plan_policy_change(operation_id,
                                      allow_unsupported=self.experimental_policies.isChecked())
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(f"Plan polityki niedostępny: {error}")
            return
        if not plan["change_needed"]:
            self.status.setText("Polityka już ustawiona; nie tworzono kopii.")
            return
        before = "brak wartości" if plan["current"] is None else str(plan["current"])
        experimental_warning = ("\nTRYB EKSPERYMENTALNY: ta edycja Windows nie jest oficjalnie wspierana. "
                                "Efekt może nie wystąpić." if not plan["supported_edition"] else "")
        answer = QMessageBox.question(self, "Zmiana polityki HKCU",
                                      f"{guide.summary}\n\nMożliwy skutek: {guide.impact}"
                                      f"{experimental_warning}\n"
                                      f"Ustawienie: {plan['label']}. Obecnie: {before}.\n"
                                      "Najpierw powstanie nowa kopia JSON. Czy wprowadzić zmianę?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            backup = new_backup_path(operation_id)
            result = apply_policy_change(operation_id, backup, accept_changes=True,
                                         allow_unsupported=self.experimental_policies.isChecked())
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie ukończono zmiany", str(error))
            return
        self.refresh_backups()
        self.status.setText(f"{result['status']}: {plan['label']}; kopia: {result['backup']}")
        if result["status"] == "APPLIED":
            self.change_summary.setText(completion_instructions(operation_id, result["backup"]))
            self.change_summary.show()

    def rollback_selected_policy(self):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        backup, _ = QFileDialog.getOpenFileName(self, "Kopia polityki REG-WRITE", "", "JSON (*.json)")
        if not backup:
            return
        try:
            preview = preview_policy_rollback(backup)
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(f"Podgląd cofnięcia niedostępny: {error}")
            return
        if preview["status"] != "PLAN":
            self.status.setText("Polityka zmieniła się od wykonania; cofnięcie odmówione.")
            return
        restore = "usunąć utworzoną wartość" if preview["restore"] is None else f"ustawić {preview['restore']}"
        answer = QMessageBox.question(self, "Cofnij politykę",
                                      f"{preview['operation']} · {preview['name']}: {restore}?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            result = rollback_policy_change(backup, accept_changes=True)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie cofnięto polityki", str(error))
            return
        self.status.setText(f"{result['status']}: {result['operation']}; kopia: {backup}")

    def apply_selected_change(self):
        guide = GUIDES[self.change_choice.currentData()]
        if guide.edition == "PRO" and not self.pro_active():
            self.status.setText("Ta zmiana wymaga podpisanej licencji PRO.")
            return
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        operation = next(item for item in CHANGE_OPERATIONS if item.id == self.change_choice.currentData())
        try:
            plan = plan_change(operation.id)
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(f"Nie można wykonać planu: {error}")
            return
        if not plan["change_needed"]:
            self.status.setText("Wartość już ustawiona; nie tworzono kopii ani zmiany.")
            return
        answer = QMessageBox.question(self, "Zmiana rejestru HKCU",
                                      f"{guide.summary}\n\nMożliwy skutek: {guide.impact}\n"
                                      f"Ustawienie: {operation.label}. Obecnie {plan['current']}, po zmianie {plan['target']}.\n"
                                      "Najpierw powstanie nowa kopia JSON. Czy wprowadzić zmianę?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            backup = new_backup_path(operation.id)
            result = apply_change(operation.id, backup, accept_changes=True)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Zmiana nieukończona", str(error))
            return
        self.refresh_backups()
        self.status.setText(f"{result['status']}: {operation.label}; kopia: {result['backup']}")
        if result["status"] == "APPLIED":
            self.change_summary.setText(completion_instructions(operation.id, result["backup"]))
            self.change_summary.show()

    def rollback_selected_change(self):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        backup, _ = QFileDialog.getOpenFileName(self, "Kopia operacji REG-WRITE", "", "JSON (*.json)")
        if not backup:
            return
        try:
            preview = preview_rollback_change(backup)
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(f"Podgląd cofnięcia niedostępny: {error}")
            return
        if preview["status"] != "PLAN":
            self.status.setText("Wartość rejestru zmieniła się od kopii; cofnięcie odmówione.")
            return
        answer = QMessageBox.question(self, "Cofnij zmianę rejestru",
                                      f"{preview['hive']}\\{preview['key']}\\{preview['name']}\n"
                                      f"Bieżąca wartość: {preview['current']} → poprzednia: {preview['restore']}?\n"
                                      "Zapis zostanie odmówiony, jeśli wartość zmieni się po podglądzie.",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            result = rollback_change(backup, accept_changes=True)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie cofnięto", str(error))
            return
        self.status.setText(f"{result['status']}: {result['operation']}; kopia: {backup}")

    def export_selected_diff(self):
        backup, _ = QFileDialog.getOpenFileName(self, "Kopia zmiany rejestru", "", "JSON (*.json)")
        if not backup:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Nowy raport różnicy", "registry-diff.json", "JSON (*.json)")
        if not destination:
            return
        try:
            report = export_change_diff(backup, destination)
            self.status.setText(f"Zapisano różnicę {report['operation']}: {destination}")
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(f"Nie wyeksportowano różnicy: {error}")

    def closeEvent(self, event):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.audit_worker.cancel_event.set()
            self.audit_worker.wait(10000)
            if self.audit_worker.isRunning():
                event.ignore()
                return
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait()
        super().closeEvent(event)
