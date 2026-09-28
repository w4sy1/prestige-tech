"""Wyłącznie odczytowa lista dysków i woluminów Windows."""

from threading import Event
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QFileDialog,
    QCheckBox,
)

from prestige_core.storage_inventory import read_disks
from prestige_core.physical_imaging import image_readonly_disk
from prestige_core.backup import backup, plan, restore, verify
from prestige_core.backup.vss import backup as vss_backup
from prestige_core.backup.vss import recover as recover_vss
from prestige_core.usb import prepare as prepare_usb, verify as verify_usb
from prestige_core.usb import update as update_usb, rollback as rollback_usb
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


class BackupWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, operation, source, destination=None, preserve_acl=False,
                 system_export=False, drivers=False, bookmarks=None, vss=False, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.source = source
        self.destination = destination
        self.preserve_acl = preserve_acl
        self.system_export = system_export
        self.drivers = drivers
        self.bookmarks = bookmarks
        self.vss = vss

    def run(self):
        try:
            if self.operation == "backup":
                options = dict(system=self.system_export, drivers=self.drivers,
                               bookmarks=[self.bookmarks] if self.bookmarks else None,
                               preserve_acl=self.preserve_acl)
                if self.vss:
                    result = vss_backup([self.source], self.destination, backup, **options)
                else:
                    result = backup([self.source], self.destination, **options)
            elif self.operation == "verify":
                result = verify(self.source)
            elif self.operation == "vss-recover":
                result = recover_vss(self.source, execute=True)
            else:
                result = restore(self.source, self.destination, apply=True,
                                 restore_acl=self.preserve_acl)
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class UsbWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, operation, path, tool=None, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.path = path
        self.tool = tool

    def run(self):
        try:
            if self.operation == "prepare":
                result = prepare_usb(self.path, [self.tool])
            elif self.operation == "verify":
                result = verify_usb(self.path)
            elif self.operation == "update":
                result = update_usb(self.path, [self.tool], prepare_usb, True)
            else:
                result = rollback_usb(self.path, True)
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class StorageWindow(QMainWindow):
    def __init__(self, *, autoload=True):
        super().__init__()
        self.setWindowTitle("PRESTIGE TECH — Storage & Recovery")
        self.resize(1120, 720)
        self.setMinimumSize(820, 560)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        self.image_worker = None
        self.backup_worker = None
        self.usb_worker = None
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
        side.addWidget(QLabel("● Kopie i odtwarzanie"))
        side.addWidget(QLabel("● Zestaw PrestigeUSB"))
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
        backup_card = QFrame()
        backup_card.setObjectName("Card")
        backup_layout = QVBoxLayout(backup_card)
        backup_layout.addWidget(QLabel("Kopia folderu — nowy katalog, bez nadpisywania"))
        backup_actions = QHBoxLayout()
        self.backup_button = QPushButton("Utwórz kopię")
        self.backup_button.clicked.connect(self.start_backup)
        backup_actions.addWidget(self.backup_button)
        self.verify_button = QPushButton("Sprawdź kopię")
        self.verify_button.clicked.connect(self.start_verify)
        backup_actions.addWidget(self.verify_button)
        self.restore_button = QPushButton("Odtwórz do nowego folderu")
        self.restore_button.clicked.connect(self.start_restore)
        backup_actions.addWidget(self.restore_button)
        backup_layout.addLayout(backup_actions)
        self.acl_checkbox = QCheckBox("Zachowaj ACL (Windows) / tryb plików")
        backup_layout.addWidget(self.acl_checkbox)
        options = QHBoxLayout()
        self.vss_checkbox = QCheckBox("VSS (Windows, administrator)")
        options.addWidget(self.vss_checkbox)
        self.system_export_checkbox = QCheckBox("Eksport systemu")
        options.addWidget(self.system_export_checkbox)
        self.drivers_checkbox = QCheckBox("Eksport sterowników")
        options.addWidget(self.drivers_checkbox)
        backup_layout.addLayout(options)
        self.bookmark_path = None
        bookmark_actions = QHBoxLayout()
        self.bookmark_button = QPushButton("Wybierz zakładki Chromium/Firefox")
        self.bookmark_button.clicked.connect(self.choose_bookmarks)
        bookmark_actions.addWidget(self.bookmark_button)
        self.bookmark_label = QLabel("Zakładki: nie wybrano")
        bookmark_actions.addWidget(self.bookmark_label, 1)
        self.vss_recover_button = QPushButton("Dziennik VSS")
        self.vss_recover_button.clicked.connect(self.start_vss_recover)
        bookmark_actions.addWidget(self.vss_recover_button)
        backup_layout.addLayout(bookmark_actions)
        main.addWidget(backup_card)
        usb_card = QFrame()
        usb_card.setObjectName("Card")
        usb_layout = QVBoxLayout(usb_card)
        usb_layout.addWidget(QLabel("PrestigeUSB — wersjonowana kopia narzędzi, bez formatowania nośnika"))
        usb_actions = QHBoxLayout()
        self.usb_buttons = []
        for label, slot in (("Utwórz zestaw", self.start_usb_prepare),
                            ("Sprawdź zestaw", self.start_usb_verify),
                            ("Aktualizuj narzędzie", self.start_usb_update),
                            ("Cofnij aktualizację", self.start_usb_rollback)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            usb_actions.addWidget(button)
            self.usb_buttons.append(button)
        usb_layout.addLayout(usb_actions)
        main.addWidget(usb_card)
        self.status = QLabel("Brak odczytu.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        layout.addWidget(content, 1)
        if autoload:
            self.refresh()

    def _run_backup_operation(self, operation, source, destination=None):
        if self.backup_worker is not None and self.backup_worker.isRunning():
            return
        self.backup_worker = BackupWorker(
            operation, source, destination, self.acl_checkbox.isChecked(),
            self.system_export_checkbox.isChecked(), self.drivers_checkbox.isChecked(),
            self.bookmark_path, self.vss_checkbox.isChecked(), self)
        for button in (self.backup_button, self.verify_button, self.restore_button,
                       self.vss_recover_button):
            button.setEnabled(False)
        self.status.setText(f"{operation}: operacja trwa…")
        self.backup_worker.loaded.connect(self.show_backup_result)
        self.backup_worker.failed.connect(self.show_backup_error)
        self.backup_worker.finished.connect(self.finish_backup_operation)
        self.backup_worker.start()

    def choose_bookmarks(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik Bookmarks Chromium lub places.sqlite Firefox", "",
            "Zakładki (Bookmarks places.sqlite *.sqlite *.db);;Wszystkie pliki (*)")
        if path:
            self.bookmark_path = path
            self.bookmark_label.setText(f"Zakładki: {Path(path).name}")

    def start_backup(self):
        source = QFileDialog.getExistingDirectory(self, "Folder źródłowy kopii")
        if not source:
            return
        parent = QFileDialog.getExistingDirectory(self, "Folder docelowy na nową kopię")
        if not parent:
            return
        destination = str(Path(parent) / f"PrestigeBackup-{uuid4().hex[:12]}")
        try:
            summary = plan([source])
            if Path(destination).is_relative_to(Path(source).resolve()):
                raise ValueError("Cel znajduje się wewnątrz źródła.")
        except (OSError, ValueError) as error:
            self.show_backup_error(str(error))
            return
        answer = QMessageBox.question(
            self, "Utwórz kopię",
            f"Skopiować {len(summary['files'])} plików ({summary['total_bytes']} bajtów) "
            f"do nowego katalogu {destination}? Pominięte znane magazyny sekretów: "
            f"{summary['excluded_count']}. "
            f"VSS: {'TAK' if self.vss_checkbox.isChecked() else 'NIE'}; "
            f"eksport systemu: {'TAK' if self.system_export_checkbox.isChecked() else 'NIE'}; "
            f"sterowniki: {'TAK' if self.drivers_checkbox.isChecked() else 'NIE'}; "
            f"zakładki: {'TAK' if self.bookmark_path else 'NIE'}.")
        if answer == QMessageBox.Yes:
            self._run_backup_operation("backup", source, destination)

    def start_verify(self):
        source = QFileDialog.getExistingDirectory(self, "Wybierz katalog kopii do sprawdzenia")
        if source:
            self._run_backup_operation("verify", source)

    def start_restore(self):
        source = QFileDialog.getExistingDirectory(self, "Wybierz katalog kopii do odtworzenia")
        if not source:
            return
        parent = QFileDialog.getExistingDirectory(self, "Folder docelowy dla nowego katalogu")
        if not parent:
            return
        destination = str(Path(parent) / f"PrestigeRestore-{uuid4().hex[:12]}")
        try:
            summary = restore(source, destination, apply=False,
                              restore_acl=self.acl_checkbox.isChecked())
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.show_backup_error(str(error))
            return
        answer = QMessageBox.question(
            self, "Odtwórz kopię",
            f"Odtworzyć {summary['files']} plików do nowego katalogu {destination}? "
            "Istniejące pliki nie będą nadpisywane.")
        if answer == QMessageBox.Yes:
            self._run_backup_operation("restore", source, destination)

    def start_vss_recover(self):
        journal, _ = QFileDialog.getOpenFileName(
            self, "Dziennik pozostałych migawek VSS", "", "Dziennik JSON (*.json)")
        if not journal:
            return
        try:
            preview = recover_vss(journal, execute=False)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.show_backup_error(str(error))
            return
        if QMessageBox.question(self, "Usuń pozostałe migawki VSS",
                                f"Usunąć {len(preview['snapshots'])} migawek "
                                "wymienionych wyłącznie w tym dzienniku?") == QMessageBox.Yes:
            self._run_backup_operation("vss-recover", journal)

    def show_backup_result(self, result):
        if result.get("ok") is False:
            self.status.setText(f"Operacja niepełna: {result}")
        else:
            self.status.setText(f"Operacja zakończona: {result}")

    def show_backup_error(self, message):
        self.status.setText(f"Błąd kopii: {message}")

    def finish_backup_operation(self):
        for button in (self.backup_button, self.verify_button, self.restore_button,
                       self.vss_recover_button):
            button.setEnabled(True)

    def _run_usb_operation(self, operation, path, tool=None):
        if self.usb_worker is not None and self.usb_worker.isRunning():
            return
        self.usb_worker = UsbWorker(operation, path, tool, self)
        for button in self.usb_buttons:
            button.setEnabled(False)
        self.status.setText(f"PrestigeUSB {operation}: operacja trwa…")
        self.usb_worker.loaded.connect(self.show_backup_result)
        self.usb_worker.failed.connect(self.show_backup_error)
        self.usb_worker.finished.connect(self.finish_usb_operation)
        self.usb_worker.start()

    def finish_usb_operation(self):
        for button in self.usb_buttons:
            button.setEnabled(True)

    def start_usb_prepare(self):
        tool = QFileDialog.getExistingDirectory(self, "Wybierz katalog narzędzia prestige-*")
        if not tool:
            return
        parent = QFileDialog.getExistingDirectory(self, "Wybierz folder docelowy PrestigeUSB")
        if not parent:
            return
        if QMessageBox.question(self, "Utwórz PrestigeUSB",
                                f"Utworzyć nowy zestaw w {parent}/PrestigeUSB z {tool}? "
                                "Nośnik nie będzie formatowany.") == QMessageBox.Yes:
            self._run_usb_operation("prepare", parent, tool)

    def start_usb_verify(self):
        root = QFileDialog.getExistingDirectory(self, "Wybierz katalog PrestigeUSB")
        if root:
            self._run_usb_operation("verify", root)

    def start_usb_update(self):
        root = QFileDialog.getExistingDirectory(self, "Wybierz istniejący katalog PrestigeUSB")
        if not root:
            return
        tool = QFileDialog.getExistingDirectory(self, "Wybierz nową wersję narzędzia prestige-*")
        if not tool:
            return
        try:
            preview = update_usb(root, [tool], prepare_usb, False)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.show_backup_error(str(error))
            return
        if QMessageBox.question(self, "Aktualizuj PrestigeUSB",
                                f"Zaktualizować {', '.join(preview['tools'])}? "
                                "Poprzednia wersja zostanie zachowana do cofnięcia.") == QMessageBox.Yes:
            self._run_usb_operation("update", root, tool)

    def start_usb_rollback(self):
        journal = QFileDialog.getExistingDirectory(self, "Wybierz Backup/Updates/<id> z journal.json")
        if not journal:
            return
        try:
            preview = rollback_usb(journal, False)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.show_backup_error(str(error))
            return
        if QMessageBox.question(self, "Cofnij aktualizację",
                                f"Przywrócić poprzednie wersje: {', '.join(preview['tools'])}? "
                                "Zmiany w plikach po aktualizacji mogą zablokować cofnięcie.") == QMessageBox.Yes:
            self._run_usb_operation("rollback", journal)

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
            "BitLocker i RAM nie są obsługiwane. Kopia folderu zapisuje manifest SHA-256, "
            "pomija znane magazyny sekretów i odtwarza wyłącznie do nowego katalogu. "
            "Opcja ACL dotyczy kopii i odtwarzania. VSS tworzy migawki Windows i wymaga "
            "administratora; po przerwaniu sprawdź dziennik VSS. Eksport systemu, "
            "sterowników i zakładek jest opcjonalny. PrestigeUSB tworzy katalog "
            "z narzędziami, sprawdza manifest, aktualizuje wersję z kopią i pozwala ją cofnąć; "
            "nie formatuje nośnika."
        )

    def closeEvent(self, event):
        if self.image_worker is not None and self.image_worker.isRunning():
            self.image_worker.cancel_event.set()
            self.image_worker.wait()
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(21000)
        if self.backup_worker is not None and self.backup_worker.isRunning():
            self.backup_worker.wait()
        if self.usb_worker is not None and self.usb_worker.isRunning():
            self.usb_worker.wait()
        super().closeEvent(event)
