"""Katalog dokumentowanych odczytów rejestru bez operacji zapisu."""

from threading import Event

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
    QLineEdit, QFileDialog, QComboBox,
)

from prestige_core.registry_read import OPERATIONS, read_operation
from prestige_core.registry_admx import load_admx_catalog
from prestige_core.registry_audit import audit_catalog
from prestige_core.registry_change import rollback_file_extensions, show_file_extensions
from prestige_core.registry_transactions import (OPERATIONS as CHANGE_OPERATIONS,
                                                  apply_change, plan_change, rollback_change)
from prestige_core.ui_theme import APP_QSS, COLORS


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
        self.catalog = list(OPERATIONS)
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
        title = QLabel("Katalog operacji rejestru")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        main.addWidget(title)
        main.addWidget(QLabel(f"{len(OPERATIONS)} odczytów ręcznych; ADMX może rozszerzyć katalog. "
                              f"{len(CHANGE_OPERATIONS) + 1} zmian HKCU z kopią (testy fixture)."))
        self.admx_button = QPushButton("Dodaj odczyty z lokalnych szablonów ADMX")
        self.admx_button.clicked.connect(self.load_admx)
        main.addWidget(self.admx_button)
        audit_actions = QHBoxLayout()
        self.audit_button = QPushButton("Audyt całego katalogu (bez zapisu wartości)")
        self.audit_button.clicked.connect(self.toggle_audit)
        audit_actions.addWidget(self.audit_button)
        main.addLayout(audit_actions)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Szukaj po ID, nazwie lub kategorii")
        self.search.textChanged.connect(self.filter_operations)
        main.addWidget(self.search)
        self.operations = QListWidget()
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
        change_actions = QHBoxLayout()
        self.extensions_button = QPushButton("Pokaż rozszerzenia plików (z kopią)")
        self.extensions_button.clicked.connect(self.apply_extensions_change)
        change_actions.addWidget(self.extensions_button)
        self.rollback_button = QPushButton("Cofnij zmianę z kopii")
        self.rollback_button.clicked.connect(self.rollback_extensions_change)
        change_actions.addWidget(self.rollback_button)
        main.addLayout(change_actions)
        additional_actions = QHBoxLayout()
        self.change_choice = QComboBox()
        for item in CHANGE_OPERATIONS:
            self.change_choice.addItem(f"{item.id}: {item.label}", item.id)
        additional_actions.addWidget(self.change_choice, 1)
        self.change_plan_button = QPushButton("Plan")
        self.change_plan_button.clicked.connect(self.plan_selected_change)
        additional_actions.addWidget(self.change_plan_button)
        self.change_apply_button = QPushButton("Zmień z kopią")
        self.change_apply_button.clicked.connect(self.apply_selected_change)
        additional_actions.addWidget(self.change_apply_button)
        self.change_rollback_button = QPushButton("Cofnij z kopii")
        self.change_rollback_button.clicked.connect(self.rollback_selected_change)
        additional_actions.addWidget(self.change_rollback_button)
        main.addLayout(additional_actions)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Wartość", "Dane", "Typ", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        card_layout.addWidget(self.table)
        main.addWidget(card, 2)
        self.status = QLabel("Brak odczytu.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        layout.addWidget(content, 1)

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
                                            "Niedostępne", str(row["type"] or "Niedostępne"), row["status"])):
                self.table.setItem(index, column, QTableWidgetItem(value))
        self.status.setText(f"{result['status']}: {result['reason'] or f'Odczytano {len(rows)} wartości.'}")

    def show_error(self, message):
        self.table.setRowCount(0)
        self.status.setText(f"Nie udało się odczytać: {message}")

    def show_help(self):
        QMessageBox.information(
            self, "Pomoc — Registry Manager",
            f"Ten etap ma {len(OPERATIONS)} ręcznie skatalogowanych operacji odczytu; "
            "może dodać osobne odczyty z lokalnych szablonów ADMX Microsoftu. "
            f"{len(CHANGE_OPERATIONS) + 1} wąskich zmian HKCU sprawdzonych na atrapach. "
            "Każda zmiana wymaga potwierdzenia i nowej kopii JSON; cofanie odmawia nadpisania wartości zmienionej później. "
            "Brak wartości lub uprawnień pokazuje jako Niedostępne. "
            "Liczba 500 jest celem, nie stanem gotowym."
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
        counts = result["counts"]
        self.status.setText(f"{result['status']}: {result['processed']}/{result['total']}; "
                            f"dostępne {counts.get('OK', 0)}, nieustawione/niedostępne "
                            f"{counts.get('Niedostępne', 0)}, błędy {counts.get('ERROR', 0)}. "
                            "Wartości nie zostały zapisane.")

    def finish_audit(self):
        self.audit_button.setText("Audyt całego katalogu (bez zapisu wartości)")
        self.admx_button.setEnabled(True)

    def apply_extensions_change(self):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        answer = QMessageBox.question(
            self, "Zmiana widoku Eksploratora",
            "Ustawić HKCU HideFileExt=0, aby pokazać rozszerzenia plików? "
            "Najpierw zapiszę kopię dotychczasowej wartości do nowego pliku JSON."
        )
        if answer != QMessageBox.Yes:
            return
        backup, _ = QFileDialog.getSaveFileName(self, "Nowa kopia przed zmianą", "registry-hidefileext-backup.json", "JSON (*.json)")
        if not backup:
            return
        try:
            result = show_file_extensions(backup, accept_changes=True)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie zmieniono rejestru", str(error))
            return
        self.status.setText("Rozszerzenia są już widoczne." if result["status"] == "ALREADY_SET"
                            else f"Zmiana zweryfikowana. Kopia: {result['backup']}")

    def rollback_extensions_change(self):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        backup, _ = QFileDialog.getOpenFileName(self, "Kopia HideFileExt", "", "JSON (*.json)")
        if not backup:
            return
        answer = QMessageBox.question(self, "Cofnij zmianę", "Przywrócić wartość HideFileExt z wybranej kopii?")
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

    def apply_selected_change(self):
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
                                      f"{operation.label}: {plan['current']} → {plan['target']}?\n"
                                      "Najpierw powstanie nowa kopia JSON; cofnięcie wymaga niezmienionej wartości.",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        backup, _ = QFileDialog.getSaveFileName(self, "Nowa kopia rejestru",
                                                operation.id.lower() + "-backup.json", "JSON (*.json)")
        if not backup:
            return
        try:
            result = apply_change(operation.id, backup, accept_changes=True)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Zmiana nieukończona", str(error))
            return
        self.status.setText(f"{result['status']}: {operation.label}; kopia: {result['backup']}")

    def rollback_selected_change(self):
        if self.audit_worker is not None and self.audit_worker.isRunning():
            self.status.setText("Najpierw zakończ audyt katalogu.")
            return
        backup, _ = QFileDialog.getOpenFileName(self, "Kopia operacji REG-WRITE", "", "JSON (*.json)")
        if not backup:
            return
        answer = QMessageBox.question(self, "Cofnij zmianę rejestru",
                                      "Przywrócić poprzednią wartość wyłącznie, jeśli nadal równa się zapisanej zmianie?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            result = rollback_change(backup, accept_changes=True)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Nie cofnięto", str(error))
            return
        self.status.setText(f"{result['status']}: {result['operation']}; kopia: {backup}")

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
