"""Wyłącznie odczytowa lista dysków i woluminów Windows."""

from threading import Event

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QFileDialog,
)

from prestige_core.storage_inventory import read_disks
from prestige_core.physical_imaging import image_readonly_disk
from prestige_core.ui_theme import APP_QSS, COLORS


class DiskWorker(QThread):
    loaded = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            self.loaded.emit(read_disks())
        except RuntimeError as error:
            self.failed.emit(str(error))


class PhysicalImageWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, number, destination, parent=None):
        super().__init__(parent)
        self.number = number
        self.destination = destination
        self.cancel_event = Event()

    def run(self):
        try:
            self.loaded.emit(image_readonly_disk(self.number, self.destination,
                                                 cancel_event=self.cancel_event))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class StorageWindow(QMainWindow):
    def __init__(self, *, autoload=True):
        super().__init__()
        self.setWindowTitle("PRESTIGE TECH — Storage & Recovery")
        self.resize(1120, 720)
        self.setMinimumSize(820, 560)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        self.image_worker = None
        self.disks = []
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
        side.addWidget(QLabel("STORAGE & RECOVERY"))
        side.addSpacing(28)
        side.addWidget(QLabel("● Dyski i woluminy"))
        side.addStretch()
        side.addWidget(QLabel("By Dominik Wasilak"))
        layout.addWidget(sidebar)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 22, 24, 22)
        title = QLabel("Fizyczne dyski widoczne w Windows")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        main.addWidget(title)
        main.addWidget(QLabel("Odczyt Get-Disk/Get-Partition. Litera woluminu nie jest identyfikatorem fizycznego nośnika."))
        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Odśwież")
        self.refresh_button.clicked.connect(self.refresh)
        actions.addWidget(self.refresh_button)
        self.image_button = QPushButton("Obraz dysku read-only")
        self.image_button.setEnabled(False)
        self.image_button.clicked.connect(self.start_physical_image)
        actions.addWidget(self.image_button)
        self.cancel_image_button = QPushButton("Przerwij obraz")
        self.cancel_image_button.setEnabled(False)
        self.cancel_image_button.clicked.connect(self.cancel_physical_image)
        actions.addWidget(self.cancel_image_button)
        self.help_button = QPushButton("?")
        self.help_button.clicked.connect(self.show_help)
        actions.addWidget(self.help_button)
        main.addLayout(actions)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Urządzenie", "Model", "Rozmiar", "Bus", "Woluminy", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_selected_disk)
        card_layout.addWidget(self.table)
        main.addWidget(card, 1)
        self.details = QLabel("Wybierz dysk, aby zobaczyć jego identyfikator.")
        self.details.setWordWrap(True)
        main.addWidget(self.details)
        self.status = QLabel("Brak odczytu.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        layout.addWidget(content, 1)
        if autoload:
            self.refresh()

    def refresh(self):
        if ((self.worker is not None and self.worker.isRunning()) or
                (self.image_worker is not None and self.image_worker.isRunning())):
            return
        self.refresh_button.setEnabled(False)
        self.status.setText("Odczytuję listę dysków…")
        self.worker = DiskWorker(self)
        self.worker.loaded.connect(self.show_disks)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(lambda: self.refresh_button.setEnabled(True))
        self.worker.start()

    def show_disks(self, disks):
        self.disks = disks
        self.image_button.setEnabled(False)
        self.table.setRowCount(len(disks))
        for index, disk in enumerate(disks):
            readonly = "tylko odczyt" if disk["read_only"] is True else "zapis możliwy" if disk["read_only"] is False else "stan zapisu nieznany"
            flags = "DYSK SYSTEMOWY; " if disk["system"] else ""
            fields = (disk["device"], disk["model"], f"{disk['size_bytes'] / 1_000_000_000:.2f} GB",
                      disk["bus"], ", ".join(disk["volumes"]) or "Brak litery", flags + readonly)
            for column, value in enumerate(fields):
                self.table.setItem(index, column, QTableWidgetItem(value))
        self.status.setText(
            f"Odczytano {len(disks)} dysków. Atrybut tylko do odczytu nie dowodzi sprzętowej blokady zapisu. "
            "Nie wykonano obrazowania ani zmian konfiguracji."
        )

    def show_selected_disk(self):
        index = self.table.currentRow()
        if not 0 <= index < len(self.disks):
            return
        disk = self.disks[index]
        self.details.setText(
            f"{disk['device']} — identyfikator: {disk['unique_id']}. "
            "Numer urządzenia i litera woluminu to różne identyfikatory."
        )
        self.image_button.setEnabled(disk["read_only"] is True and not disk["system"])

    def start_physical_image(self):
        index = self.table.currentRow()
        if not 0 <= index < len(self.disks):
            return
        disk = self.disks[index]
        if disk["read_only"] is not True or disk["system"]:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Nowy obraz RAW na innym dysku", "disk.img", "Obraz RAW (*.img)")
        if not destination:
            return
        answer = QMessageBox.question(
            self, "Obraz dysku fizycznego",
            f"Czytać {disk['device']} ({disk['size_bytes']} bajtów) do nowego pliku {destination}? "
            "Atrybut read-only Windows nie jest sprzętową blokadą zapisu. "
            "Cel musi być na innym dysku; operacja może trwać długo."
        )
        if answer != QMessageBox.Yes:
            return
        self.image_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.cancel_image_button.setEnabled(True)
        self.status.setText("Obrazowanie w toku; źródło otwierane tylko do odczytu…")
        self.image_worker = PhysicalImageWorker(disk["number"], destination, self)
        self.image_worker.loaded.connect(self.show_image_result)
        self.image_worker.failed.connect(self.show_image_error)
        self.image_worker.finished.connect(self.finish_physical_image)
        self.image_worker.start()

    def cancel_physical_image(self):
        if self.image_worker is not None and self.image_worker.isRunning():
            self.image_worker.cancel_event.set()
            self.status.setText("Przerywam obrazowanie po bieżącym bloku…")

    def show_image_result(self, result):
        self.status.setText(
            f"{result['status']}: {result['read_bytes']}/{result['expected_bytes']} bajtów, "
            f"weryfikacja SHA-256: {'TAK' if result['verified_image'] else 'NIE'}. "
            f"{result['error'] or 'Metadane zapisane obok obrazu.'}"
        )

    def show_image_error(self, message):
        self.status.setText(f"Nie utworzono kompletnego obrazu: {message}")

    def finish_physical_image(self):
        self.refresh_button.setEnabled(True)
        self.cancel_image_button.setEnabled(False)
        self.show_selected_disk()

    def show_error(self, message):
        self.disks = []
        self.image_button.setEnabled(False)
        self.table.setRowCount(0)
        self.details.setText("Identyfikator niedostępny.")
        self.status.setText(f"Niedostępne: {message}")

    def show_help(self):
        QMessageBox.information(
            self, "Pomoc — Storage & Recovery",
            "Lista identyfikuje dyski i litery woluminów. Obraz RAW jest dostępny tylko dla "
            "niesystemowego dysku z atrybutem read-only i celu na innym dysku. Otwiera źródło "
            "wyłącznie do odczytu, tworzy nowy .img i weryfikuje SHA-256. Get-Disk może pomijać "
            "dyski dynamiczne. Atrybut read-only Windows nie daje gwarancji sprzętowej blokady zapisu; "
            "BitLocker i RAM nie są obsługiwane."
        )

    def closeEvent(self, event):
        if self.image_worker is not None and self.image_worker.isRunning():
            self.image_worker.cancel_event.set()
            self.image_worker.wait()
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(21000)
        super().closeEvent(event)
