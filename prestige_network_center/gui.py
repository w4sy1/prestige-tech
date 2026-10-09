"""Pierwszy działający ekran Network Center oparty na danych systemowych."""

import json
import os
from pathlib import Path
import sqlite3
from datetime import datetime
from threading import Event

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QTabWidget, QInputDialog,
    QLineEdit, QSpinBox, QCheckBox, QPlainTextEdit, QComboBox,
)

from prestige_core.network import read_adapters, read_neighbors
from prestige_core.network_snapshot import (compare_snapshots, make_snapshot, save_snapshot,
                                            snapshot_from_json_list)
from prestige_core.network_discovery import load_oui, local_scopes, scan_local_scope
from prestige_core.internet_diagnostic import diagnose
from prestige_core.internet_context import correlate_diagnostic, read_context
from prestige_core.nmap_profiles import PROFILES, compare_results, parse_xml, plan_profile, run_profile
from prestige_core.device_history import DeviceHistory, LAN_CATEGORIES, load_observation_json
from prestige_core.lan_legacy_import import import_legacy_lan
from prestige_core.network_optimizer import inspect_adapter
from prestige_core.network_dns_change import (WindowsDnsBackend, apply_dns_change,
                                              plan_dns_change, rollback_dns_change)
from prestige_core.network_dns_ipv6_change import (WindowsIpv6DnsBackend, apply_ipv6_dns_change,
                                                   plan_ipv6_dns_change, rollback_ipv6_dns_change)
from prestige_core.network_dns_backups import list_dns_backups
from prestige_core.network_report import export_network_report
from prestige_core.windows_repairs import plan_repair, run_repair, list_repair_journals
from prestige_core.report_live import summarize_live_result
from prestige_report.gui import ReportDialog
from prestige_core.dns_benchmark import benchmark as benchmark_dns
from prestige_core.dns_system import read_doh_state, system_dns_test
from prestige_core.dns_history import DnsHistory
from prestige_core.dns_profiles import (PROFILES as DNS_PROFILES,
                                        discovery_candidates, get_profile)
from prestige_core.network_mtu_change import (WindowsMtuBackend, apply_mtu_change,
                                              plan_mtu_change, rollback_mtu_change)
from prestige_core.traffic_analysis import analyze_log
from prestige_core.traffic_stream import RollingDetector, TrafficStream
from prestige_core.traffic_capture import capture_syn
from prestige_core.sentinel_deep_capture import capture as deep_capture, list_interfaces
from prestige_core.sentinel_status import read_sentinel_events, read_sentinel_status
from prestige_core.sentinel_history import read_device_history
from prestige_core.sentinel_trust import change_trust, rollback_trust
from prestige_core.sentinel_devices import (assess_observations, correlate_devices,
                                            read_device_registry)
from prestige_core.sentinel_firewall import WindowsFirewallBackend, change_block
from prestige_core.sentinel_policy import ProtectionPolicy
from prestige_core.ui_theme import APP_QSS, COLORS


def network_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor(COLORS["info"]), 4))
    for a, b in [((32, 12), (13, 48)), ((32, 12), (51, 48)), ((13, 48), (51, 48))]:
        painter.drawLine(*a, *b)
    painter.setBrush(QBrush(QColor(COLORS["primary"])))
    for x, y in ((32, 12), (13, 48), (51, 48)):
        painter.drawEllipse(x - 6, y - 6, 12, 12)
    painter.end()
    return QIcon(pixmap)


class NeighborWorker(QThread):
    loaded = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            self.loaded.emit(read_neighbors())
        except RuntimeError as error:
            self.failed.emit(str(error))


class AdapterWorker(QThread):
    loaded = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            self.loaded.emit(read_adapters())
        except RuntimeError as error:
            self.failed.emit(str(error))


class ScopeWorker(QThread):
    loaded = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            self.loaded.emit(local_scopes())
        except RuntimeError as error:
            self.failed.emit(str(error))


class DiscoveryWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, scope, oui, resolve_names, use_nmap=False, parent=None):
        super().__init__(parent)
        self.scope = scope
        self.oui = oui
        self.resolve_names = resolve_names
        self.use_nmap = use_nmap
        self.cancel_event = Event()

    def run(self):
        try:
            self.loaded.emit(scan_local_scope(self.scope["scope"], self.scope["ip"],
                                              cancel_event=self.cancel_event, oui=self.oui,
                                              resolve_names=self.resolve_names,
                                              use_nmap=self.use_nmap))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class InternetWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, target, gateway, count, traceroute, mtu, http, parent=None):
        super().__init__(parent)
        self.target, self.gateway, self.count = target, gateway, count
        self.traceroute, self.mtu, self.http = traceroute, mtu, http
        self.cancel_event = Event()

    def run(self):
        try:
            result = diagnose(self.target, gateway=self.gateway, count=self.count,
                              traceroute=self.traceroute, test_mtu=self.mtu,
                              test_http=self.http,
                              cancel_event=self.cancel_event)
            if result["status"] == "COMPLETE" and not self.cancel_event.is_set():
                try:
                    context = read_context()
                except (OSError, ValueError, RuntimeError) as error:
                    context = {"status": "UNKNOWN", "wifi": {}, "errors": [type(error).__name__]}
                result["link_context"] = correlate_diagnostic(result, context)
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class InternetContextWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            self.loaded.emit(read_context())
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class DnsBenchmarkWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, servers, count, parent=None):
        super().__init__(parent)
        self.servers, self.count = servers, count
        self.cancel_event = Event()

    def run(self):
        try:
            self.loaded.emit(benchmark_dns(self.servers, count=self.count,
                                           cancel_event=self.cancel_event))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class DnsSystemWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action

    def run(self):
        try:
            self.loaded.emit(read_doh_state() if self.action == "doh"
                             else system_dns_test())
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class NmapWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, profile, target, directory, authorized, parent=None):
        super().__init__(parent)
        self.profile, self.target = profile, target
        self.directory, self.authorized = directory, authorized
        self.cancel_event = Event()

    def run(self):
        try:
            self.loaded.emit(run_profile(self.profile, self.target, self.directory,
                                         authorized=self.authorized, cancel_event=self.cancel_event))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class OptimizerWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index

    def run(self):
        try:
            self.loaded.emit(inspect_adapter(self.index))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class NetworkRepairWorker(QThread):
    loaded = Signal(dict)
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


class DnsChangeWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, action, *, index=None, servers=None, backup=None, family="IPv4", parent=None):
        super().__init__(parent)
        self.action, self.index, self.servers, self.backup = action, index, servers, backup
        self.family = family

    def run(self):
        try:
            ipv6 = self.family == "IPv6"
            backend = WindowsIpv6DnsBackend() if ipv6 else WindowsDnsBackend()
            if self.action == "plan":
                plan = plan_ipv6_dns_change if ipv6 else plan_dns_change
                result = {"status": "PLAN", **plan(self.index, self.servers, backend)}
            elif self.action == "apply":
                apply = apply_ipv6_dns_change if ipv6 else apply_dns_change
                result = apply(self.index, self.servers, self.backup, backend)
            elif self.action == "rollback":
                rollback = rollback_ipv6_dns_change if ipv6 else rollback_dns_change
                result = rollback(self.backup, backend, apply=True)
            else:
                raise ValueError("Nieprawidłowa operacja DNS.")
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError, FileExistsError) as error:
            self.failed.emit(str(error))


class MtuChangeWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, action, *, index=None, value=None, target=None, backup=None, parent=None):
        super().__init__(parent)
        self.action, self.index, self.value, self.target, self.backup = action, index, value, target, backup

    def run(self):
        try:
            backend = WindowsMtuBackend()
            if self.action == "plan":
                result = {"status": "PLAN", **plan_mtu_change(self.index, self.value, self.target, backend)}
            elif self.action == "apply":
                result = apply_mtu_change(self.index, self.value, self.target, self.backup, backend)
            elif self.action == "rollback":
                result = rollback_mtu_change(self.backup, backend, apply=True)
            else:
                raise ValueError("Nieprawidłowa operacja MTU.")
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError, FileExistsError) as error:
            self.failed.emit(str(error))


class TrafficWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, path, kind, local_ips, offset, parent=None):
        super().__init__(parent)
        self.path, self.kind, self.local_ips, self.offset = path, kind, local_ips, offset

    def run(self):
        try:
            self.loaded.emit(analyze_log(self.path, self.kind, self.local_ips,
                                         utc_offset=self.offset))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class TrafficStreamWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, stream, parent=None):
        super().__init__(parent)
        self.stream = stream

    def run(self):
        try:
            self.loaded.emit(self.stream.poll())
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class TrafficCaptureWorker(QThread):
    alert = Signal(dict)
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, local_ip, seconds=30, parent=None):
        super().__init__(parent)
        self.local_ip, self.seconds = local_ip, seconds
        self.cancel_event = Event()

    def run(self):
        detector = RollingDetector([self.local_ip])
        def on_event(row):
            alert = detector.process(row)
            if alert is not None:
                self.alert.emit(alert)
        try:
            self.loaded.emit(capture_syn(self.local_ip, seconds=self.seconds,
                                         cancel_event=self.cancel_event, on_event=on_event))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class DeepCaptureWorker(QThread):
    alert = Signal(dict)
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, interface, local_ips, seconds, parent=None):
        super().__init__(parent)
        self.interface, self.local_ips, self.seconds = interface, local_ips, seconds
        self.cancel_event = Event()

    def run(self):
        try:
            self.loaded.emit(deep_capture(self.interface, seconds=self.seconds,
                                          local_ips=self.local_ips,
                                          cancel_event=self.cancel_event,
                                          on_alert=self.alert.emit))
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class FirewallWorker(QThread):
    loaded = Signal(dict)
    failed = Signal(str)

    def __init__(self, address, enable, apply, parent=None):
        super().__init__(parent)
        self.address, self.enable, self.apply = address, enable, apply

    def run(self):
        try:
            result = change_block(self.address, WindowsFirewallBackend(),
                                  enable=self.enable, apply=self.apply)
            self.loaded.emit(result)
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))


class NetworkCenterWindow(QMainWindow):
    def __init__(self, *, autoload=True):
        super().__init__()
        self.setWindowTitle("PRESTIGE TECH — Network Center")
        self.setWindowIcon(network_icon())
        self.resize(1120, 720)
        self.setMinimumSize(820, 560)
        self.setStyleSheet(APP_QSS)
        self.worker = None
        self.adapter_worker = None
        self.scope_worker = None
        self.discovery_worker = None
        self.internet_worker = None
        self.internet_context_worker = None
        self.dns_benchmark_worker = None
        self.dns_system_worker = None
        self.nmap_worker = None
        self.device_history = None
        self.dns_history = None
        self.optimizer_worker = None
        self.network_repair_worker = None
        self.dns_change_worker = None
        self.mtu_change_worker = None
        self.traffic_worker = None
        self.traffic_stream_worker = None
        self.traffic_capture_worker = None
        self.deep_capture_worker = None
        self.traffic_stream = None
        self.traffic_timer = QTimer(self)
        self.traffic_timer.setInterval(3000)
        self.traffic_timer.timeout.connect(self.poll_traffic_stream)
        self.firewall_worker = None
        self.auto_firewall_worker = None
        self.auto_firewall_address = None
        self.sentinel_registry_result = None
        self.sentinel_registry_folder = None
        self.protection_policy = None
        self.neighbors_data = None
        self.adapters_data = None
        self.last_discovery_result = None
        self.report_dialog = None
        self.last_discovery_scope = None
        self.scheduled_scope = None
        self.scheduled_remaining = 0
        self.discovery_timer = QTimer(self)
        self.discovery_timer.timeout.connect(self.run_scheduled_discovery)
        self.discovery_oui = {}

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
        side.addWidget(QLabel("NETWORK CENTER"))
        side.addSpacing(28)
        overview = QLabel("● Przegląd sieci")
        overview.setStyleSheet(f"color: {COLORS['info']}; font-weight: 700; padding: 9px;")
        overview.setToolTip("Bieżąca sekcja: urządzenia zapisane w lokalnej tablicy sąsiadów.")
        side.addWidget(overview)
        side.addStretch()
        side.addWidget(QLabel("By Dominik Wasilak"))
        layout.addWidget(sidebar)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 22, 24, 22)
        title = QLabel("Stan lokalnej sieci")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        main.addWidget(title)
        main.addWidget(QLabel("Adaptery, DNS i lokalna tablica sąsiadów. Wpis w cache nie dowodzi, że urządzenie jest teraz online."))
        header = QHBoxLayout()
        self.count = QLabel("Brak odczytu")
        self.count.setStyleSheet(f"color: {COLORS['info']}; font-size: 13pt;")
        header.addWidget(self.count)
        header.addStretch()
        self.help_button = QPushButton("?")
        self.help_button.setToolTip("Wyjaśnienie źródła danych i ograniczeń odczytu")
        self.help_button.clicked.connect(self.show_help)
        header.addWidget(self.help_button)
        self.save_button = QPushButton("Zapisz migawkę")
        self.save_button.setEnabled(False)
        self.save_button.setToolTip("Zapisz nowy plik JSON z lokalnymi adresami IP i MAC")
        self.save_button.clicked.connect(self.save_current_snapshot)
        header.addWidget(self.save_button)
        self.import_snapshot_button = QPushButton("Migawka z listy JSON")
        self.import_snapshot_button.clicked.connect(self.save_imported_snapshot)
        header.addWidget(self.import_snapshot_button)
        self.compare_button = QPushButton("Porównaj migawki")
        self.compare_button.clicked.connect(self.choose_snapshots_to_compare)
        header.addWidget(self.compare_button)
        self.refresh_button = QPushButton("Odśwież")
        self.refresh_button.setToolTip("Ponownie odczytaj lokalny cache bez skanowania sieci.")
        self.refresh_button.clicked.connect(self.refresh)
        header.addWidget(self.refresh_button)
        main.addLayout(header)
        tabs = QTabWidget()
        self.tabs = tabs
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Adresy IPv4", "MAC", "Stan cache", "Interfejs"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        card_layout.addWidget(self.table)
        tabs.addTab(card, "Urządzenia")
        discovery_card = QFrame()
        discovery_card.setObjectName("Card")
        discovery_layout = QVBoxLayout(discovery_card)
        discovery_actions = QHBoxLayout()
        self.discover_button = QPushButton("Skanuj lokalną podsieć")
        self.discover_button.clicked.connect(self.start_discovery)
        discovery_actions.addWidget(self.discover_button)
        self.stop_discovery_button = QPushButton("Przerwij skan")
        self.stop_discovery_button.setEnabled(False)
        self.stop_discovery_button.clicked.connect(self.stop_discovery)
        discovery_actions.addWidget(self.stop_discovery_button)
        discovery_layout.addLayout(discovery_actions)
        discovery_options = QHBoxLayout()
        self.discovery_names = QCheckBox("Reverse DNS (do 3 s na host)")
        discovery_options.addWidget(self.discovery_names)
        self.discovery_nmap = QCheckBox("Nmap -sn (opcjonalnie, do 45 s)")
        discovery_options.addWidget(self.discovery_nmap)
        schedule = QHBoxLayout()
        self.schedule_minutes = QSpinBox()
        self.schedule_minutes.setRange(15, 120)
        self.schedule_minutes.setValue(30)
        self.schedule_minutes.setSuffix(" min między skanami")
        schedule.addWidget(self.schedule_minutes)
        self.schedule_runs = QSpinBox()
        self.schedule_runs.setRange(1, 12)
        self.schedule_runs.setValue(3)
        self.schedule_runs.setSuffix(" skany")
        schedule.addWidget(self.schedule_runs)
        schedule_start = QPushButton("Włącz harmonogram ICMP")
        schedule_start.clicked.connect(self.start_discovery_schedule)
        schedule.addWidget(schedule_start)
        schedule_stop = QPushButton("Wyłącz harmonogram")
        schedule_stop.clicked.connect(self.stop_discovery_schedule)
        schedule.addWidget(schedule_stop)
        discovery_layout.addLayout(schedule)
        self.discovery_oui_button = QPushButton("Wczytaj lokalną bazę OUI")
        self.discovery_oui_button.clicked.connect(self.choose_discovery_oui)
        discovery_options.addWidget(self.discovery_oui_button)
        discovery_layout.addLayout(discovery_options)
        self.discovery_note = QLabel("Nie wykonano skanu ICMP.")
        self.discovery_note.setWordWrap(True)
        discovery_layout.addWidget(self.discovery_note)
        self.report_button = QPushButton("Ostatni skan LAN → Repair Report")
        self.report_button.setEnabled(False)
        self.report_button.clicked.connect(self.open_discovery_report)
        discovery_layout.addWidget(self.report_button)
        self.discovery_table = QTableWidget(0, 5)
        self.discovery_table.setHorizontalHeaderLabels(["IP", "MAC z cache", "Nazwa", "Producent", "Dowód"])
        self.discovery_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.discovery_table.setEditTriggers(QTableWidget.NoEditTriggers)
        discovery_layout.addWidget(self.discovery_table, 1)
        tabs.addTab(discovery_card, "Skan lokalny")
        internet_card = QFrame()
        internet_card.setObjectName("Card")
        internet_layout = QVBoxLayout(internet_card)
        internet_layout.addWidget(QLabel("Pomiar świadomie wskazanego adresu IP; brama zostanie pobrana z adaptera."))
        self.internet_help_button = QPushButton("Mam problem z Internetem — zacznij diagnozę")
        self.internet_help_button.clicked.connect(self.start_guided_internet_diagnostic)
        internet_layout.addWidget(self.internet_help_button)
        internet_actions = QHBoxLayout()
        self.internet_target = QLineEdit()
        self.internet_target.setPlaceholderText("IPv4 lub IPv6 celu")
        internet_actions.addWidget(self.internet_target)
        self.internet_count = QSpinBox()
        self.internet_count.setRange(2, 100)
        self.internet_count.setValue(5)
        internet_actions.addWidget(self.internet_count)
        self.internet_trace = QCheckBox("Trasa")
        internet_actions.addWidget(self.internet_trace)
        self.internet_mtu = QCheckBox("MTU IPv4")
        internet_actions.addWidget(self.internet_mtu)
        self.internet_http = QCheckBox("HTTP/HTTPS do example.com")
        internet_actions.addWidget(self.internet_http)
        self.internet_button = QPushButton("Zbadaj połączenie")
        self.internet_button.clicked.connect(self.start_internet_diagnostic)
        internet_actions.addWidget(self.internet_button)
        self.internet_context_button = QPushButton("Kontekst łącza")
        self.internet_context_button.clicked.connect(self.start_internet_context)
        internet_actions.addWidget(self.internet_context_button)
        self.internet_cancel_button = QPushButton("Przerwij")
        self.internet_cancel_button.setEnabled(False)
        self.internet_cancel_button.clicked.connect(self.cancel_internet_diagnostic)
        internet_actions.addWidget(self.internet_cancel_button)
        internet_layout.addLayout(internet_actions)
        self.internet_result = QLabel("Nie wykonano pomiaru.")
        self.internet_result.setWordWrap(True)
        internet_layout.addWidget(self.internet_result)
        self.internet_plan_button = QPushButton("Zobacz bezpieczny plan naprawy")
        self.internet_plan_button.setEnabled(False)
        self.internet_plan_button.clicked.connect(self.show_guided_internet_plan)
        internet_layout.addWidget(self.internet_plan_button)
        self.internet_trace_output = QPlainTextEdit()
        self.internet_trace_output.setReadOnly(True)
        self.internet_trace_output.setPlaceholderText("Wynik opcjonalnego traceroute pojawi się tutaj.")
        internet_layout.addWidget(self.internet_trace_output, 1)
        tabs.addTab(internet_card, "Internet")
        dns_card = QFrame()
        dns_card.setObjectName("Card")
        dns_layout = QVBoxLayout(dns_card)
        dns_layout.addWidget(QLabel("Porównanie resolverów na podstawie nowych zapytań DNS. Nie zmienia ustawień."))
        dns_controls = QHBoxLayout()
        self.dns_profile = QComboBox()
        for key, profile in DNS_PROFILES.items():
            self.dns_profile.addItem(profile["name"], key)
        dns_controls.addWidget(self.dns_profile)
        self.dns_profile_button = QPushButton("Wstaw adresy profilu do planu")
        self.dns_profile_button.clicked.connect(self.use_dns_profile)
        dns_controls.addWidget(self.dns_profile_button)
        self.dns_benchmark_count = QSpinBox()
        self.dns_benchmark_count.setRange(1, 50)
        self.dns_benchmark_count.setValue(3)
        self.dns_benchmark_count.setSuffix(" prób")
        dns_controls.addWidget(self.dns_benchmark_count)
        self.dns_benchmark_button = QPushButton("Porównaj resolvery")
        self.dns_benchmark_button.clicked.connect(self.start_dns_benchmark)
        dns_controls.addWidget(self.dns_benchmark_button)
        self.dns_benchmark_stop = QPushButton("Przerwij")
        self.dns_benchmark_stop.setEnabled(False)
        self.dns_benchmark_stop.clicked.connect(self.stop_dns_benchmark)
        dns_controls.addWidget(self.dns_benchmark_stop)
        dns_layout.addLayout(dns_controls)
        dns_sources = QHBoxLayout()
        self.dns_include_system = QCheckBox("Dodaj aktualny DNS systemu")
        self.dns_include_system.setChecked(True)
        dns_sources.addWidget(self.dns_include_system)
        self.dns_include_gateway = QCheckBox("Dodaj bramę (DNS niepotwierdzony)")
        dns_sources.addWidget(self.dns_include_gateway)
        dns_layout.addLayout(dns_sources)
        dns_checks = QHBoxLayout()
        self.dns_doh_button = QPushButton("Odczytaj status DoH Windows")
        self.dns_doh_button.clicked.connect(lambda: self.start_dns_system("doh"))
        dns_checks.addWidget(self.dns_doh_button)
        self.dns_system_button = QPushButton("Test systemowego DNS")
        self.dns_system_button.clicked.connect(lambda: self.start_dns_system("resolve"))
        dns_checks.addWidget(self.dns_system_button)
        dns_layout.addLayout(dns_checks)
        dns_history_actions = QHBoxLayout()
        self.dns_history_button = QPushButton("Włącz lokalną historię DNS")
        self.dns_history_button.clicked.connect(self.toggle_dns_history)
        dns_history_actions.addWidget(self.dns_history_button)
        self.dns_history_show = QPushButton("Pokaż ostatnie wyniki")
        self.dns_history_show.clicked.connect(self.show_dns_history)
        dns_history_actions.addWidget(self.dns_history_show)
        dns_layout.addLayout(dns_history_actions)
        self.dns_history_note = QLabel("Historia wyłączona; wyniki nie są zapisywane.")
        self.dns_history_note.setWordWrap(True)
        dns_layout.addWidget(self.dns_history_note)
        self.dns_benchmark_note = QLabel("Wybierz profil albo porównaj osiem publicznych resolverów.")
        self.dns_benchmark_note.setWordWrap(True)
        dns_layout.addWidget(self.dns_benchmark_note)
        self.dns_benchmark_output = QPlainTextEdit()
        self.dns_benchmark_output.setReadOnly(True)
        dns_layout.addWidget(self.dns_benchmark_output, 1)
        tabs.addTab(dns_card, "DNS Center")
        nmap_card = QFrame()
        nmap_card.setObjectName("Card")
        nmap_layout = QVBoxLayout(nmap_card)
        nmap_actions = QHBoxLayout()
        self.nmap_profile = QComboBox()
        self.nmap_profile.addItems(PROFILES)
        nmap_actions.addWidget(self.nmap_profile)
        self.nmap_target = QLineEdit("127.0.0.1")
        self.nmap_target.setPlaceholderText("Własny lub uzgodniony adres/cel")
        nmap_actions.addWidget(self.nmap_target)
        self.nmap_authorized = QCheckBox("Mam zgodę na skan tego celu")
        nmap_actions.addWidget(self.nmap_authorized)
        self.nmap_button = QPushButton("Uruchom profil")
        self.nmap_button.clicked.connect(self.start_nmap)
        nmap_actions.addWidget(self.nmap_button)
        self.nmap_cancel_button = QPushButton("Przerwij")
        self.nmap_cancel_button.setEnabled(False)
        self.nmap_cancel_button.clicked.connect(self.cancel_nmap)
        nmap_actions.addWidget(self.nmap_cancel_button)
        nmap_layout.addLayout(nmap_actions)
        self.nmap_compare_button = QPushButton("Porównaj dwa pliki XML Nmap")
        self.nmap_compare_button.clicked.connect(self.compare_nmap_files)
        nmap_layout.addWidget(self.nmap_compare_button)
        self.nmap_note = QLabel("Wybierz profil i cel. Nmap musi być zainstalowany w systemie.")
        self.nmap_note.setWordWrap(True)
        nmap_layout.addWidget(self.nmap_note)
        self.nmap_output = QPlainTextEdit()
        self.nmap_output.setReadOnly(True)
        nmap_layout.addWidget(self.nmap_output, 1)
        tabs.addTab(nmap_card, "Porty (Nmap)")
        local_history_card = QFrame()
        local_history_card.setObjectName("Card")
        local_history_layout = QVBoxLayout(local_history_card)
        self.local_history_button = QPushButton("Włącz lokalną historię LAN")
        self.local_history_button.clicked.connect(self.toggle_local_history)
        local_history_layout.addWidget(self.local_history_button)
        self.import_lan_button = QPushButton("Importuj starą bazę LAN Radar do nowego pliku")
        self.import_lan_button.clicked.connect(self.import_legacy_lan_history)
        local_history_layout.addWidget(self.import_lan_button)
        self.import_observation_button = QPushButton("Importuj obserwację LAN z JSON")
        self.import_observation_button.clicked.connect(self.import_lan_observation)
        local_history_layout.addWidget(self.import_observation_button)
        self.local_devices_table = QTableWidget(0, 4)
        self.local_devices_table.setHorizontalHeaderLabels(["MAC", "Adresy IP", "Nazwa", "Kategoria"])
        self.local_devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.local_devices_table.setEditTriggers(QTableWidget.NoEditTriggers)
        local_history_layout.addWidget(self.local_devices_table, 1)
        self.tag_lan_button = QPushButton("Ustaw kategorię wybranego urządzenia")
        self.tag_lan_button.clicked.connect(self.tag_selected_lan_device)
        local_history_layout.addWidget(self.tag_lan_button)
        self.local_history_note = QLabel("Historia wyłączona; baza nie jest tworzona bez wyboru użytkownika.")
        self.local_history_note.setWordWrap(True)
        local_history_layout.addWidget(self.local_history_note)
        self.local_history_table = QTableWidget(0, 4)
        self.local_history_table.setHorizontalHeaderLabels(["Czas UTC", "MAC", "Zdarzenie", "Szczegóły"])
        self.local_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.local_history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        local_history_layout.addWidget(self.local_history_table, 1)
        tabs.addTab(local_history_card, "Historia LAN")
        optimizer_card = QFrame()
        optimizer_card.setObjectName("Card")
        optimizer_layout = QVBoxLayout(optimizer_card)
        optimizer_actions = QHBoxLayout()
        self.optimizer_adapter = QComboBox()
        optimizer_actions.addWidget(self.optimizer_adapter)
        self.optimizer_button = QPushButton("Odczytaj ustawienia")
        self.optimizer_button.clicked.connect(self.start_optimizer_read)
        optimizer_actions.addWidget(self.optimizer_button)
        optimizer_layout.addLayout(optimizer_actions)
        dns_actions = QHBoxLayout()
        self.dns_addresses = QLineEdit()
        self.dns_family = QComboBox()
        self.dns_family.addItems(["IPv4", "IPv6"])
        self.dns_family.currentTextChanged.connect(
            lambda family: self.dns_addresses.setPlaceholderText(
                f"DNS {family}, oddzielone przecinkiem; puste = automatycznie"))
        dns_actions.addWidget(self.dns_family)
        self.dns_addresses.setPlaceholderText("DNS IPv4, oddzielone przecinkiem; puste = automatycznie")
        dns_actions.addWidget(self.dns_addresses)
        self.dns_plan_button = QPushButton("Plan DNS")
        self.dns_plan_button.clicked.connect(lambda: self.start_dns_change("plan"))
        dns_actions.addWidget(self.dns_plan_button)
        self.dns_apply_button = QPushButton("Zmień DNS z kopią")
        self.dns_apply_button.clicked.connect(lambda: self.start_dns_change("apply"))
        dns_actions.addWidget(self.dns_apply_button)
        self.dns_rollback_button = QPushButton("Cofnij DNS z kopii")
        self.dns_rollback_button.clicked.connect(lambda: self.start_dns_change("rollback"))
        dns_actions.addWidget(self.dns_rollback_button)
        optimizer_layout.addLayout(dns_actions)
        backups_button = QPushButton("Lista kopii DNS")
        backups_button.clicked.connect(self.show_dns_backups)
        optimizer_layout.addWidget(backups_button)
        mtu_actions = QHBoxLayout()
        self.mtu_value = QSpinBox()
        self.mtu_value.setRange(576, 1500)
        self.mtu_value.setValue(1400)
        mtu_actions.addWidget(self.mtu_value)
        self.mtu_plan_button = QPushButton("Plan MTU")
        self.mtu_plan_button.clicked.connect(lambda: self.start_mtu_change("plan"))
        mtu_actions.addWidget(self.mtu_plan_button)
        self.mtu_apply_button = QPushButton("Zmień MTU z kopią")
        self.mtu_apply_button.clicked.connect(lambda: self.start_mtu_change("apply"))
        mtu_actions.addWidget(self.mtu_apply_button)
        self.mtu_rollback_button = QPushButton("Cofnij MTU z kopii")
        self.mtu_rollback_button.clicked.connect(lambda: self.start_mtu_change("rollback"))
        mtu_actions.addWidget(self.mtu_rollback_button)
        optimizer_layout.addLayout(mtu_actions)
        self.optimizer_note = QLabel("Odczyt DNS, MTU, TCP i zasilania. Zmiana DNS wymaga administratora i nowej kopii JSON.")
        self.optimizer_note.setWordWrap(True)
        optimizer_layout.addWidget(self.optimizer_note)
        self.optimizer_output = QPlainTextEdit()
        self.optimizer_output.setReadOnly(True)
        optimizer_layout.addWidget(self.optimizer_output, 1)
        tabs.addTab(optimizer_card, "Optymalizacja")
        repair_card = QFrame()
        repair_card.setObjectName("Card")
        repair_layout = QVBoxLayout(repair_card)
        repair_layout.addWidget(QLabel("Naprawy Windows: wymagają administratora, zapisują dziennik i nie mają gwarantowanego cofnięcia."))
        repair_actions = QHBoxLayout()
        self.network_repair_operation = QComboBox()
        for operation, label in (("flush-dns", "Wyczyść cache DNS"),
                                 ("dhcp-renew", "Odnów DHCP"),
                                 ("winsock-reset", "Reset Winsock")):
            self.network_repair_operation.addItem(label, operation)
        repair_actions.addWidget(self.network_repair_operation)
        self.network_repair_plan_button = QPushButton("Pokaż plan")
        self.network_repair_plan_button.clicked.connect(self.show_network_repair_plan)
        repair_actions.addWidget(self.network_repair_plan_button)
        self.network_repair_run_button = QPushButton("Wykonaj po potwierdzeniu")
        self.network_repair_run_button.clicked.connect(self.start_network_repair)
        repair_actions.addWidget(self.network_repair_run_button)
        repair_layout.addLayout(repair_actions)
        journals_button = QPushButton("Odczytaj dzienniki napraw")
        journals_button.clicked.connect(self.show_network_repair_journals)
        repair_layout.addWidget(journals_button)
        self.network_repair_output = QPlainTextEdit()
        self.network_repair_output.setReadOnly(True)
        repair_layout.addWidget(self.network_repair_output, 1)
        tabs.addTab(repair_card, "Naprawa sieci")
        traffic_card = QFrame()
        traffic_card.setObjectName("Card")
        traffic_layout = QVBoxLayout(traffic_card)
        traffic_actions = QHBoxLayout()
        self.traffic_kind = QComboBox()
        self.traffic_kind.addItems(["windows", "jsonl", "linux"])
        traffic_actions.addWidget(self.traffic_kind)
        self.traffic_offset = QLineEdit(datetime.now().astimezone().strftime("%z"))
        self.traffic_offset.setPlaceholderText("Offset +0200 dla logu Windows")
        self.traffic_offset.setMaximumWidth(110)
        traffic_actions.addWidget(self.traffic_offset)
        self.traffic_button = QPushButton("Analizuj log ruchu")
        self.traffic_button.clicked.connect(self.choose_traffic_log)
        traffic_actions.addWidget(self.traffic_button)
        self.traffic_stream_button = QPushButton("Śledź rosnący log")
        self.traffic_stream_button.clicked.connect(self.toggle_traffic_stream)
        traffic_actions.addWidget(self.traffic_stream_button)
        self.traffic_capture_button = QPushButton("TCP SYN na żywo (30 s)")
        self.traffic_capture_button.clicked.connect(self.toggle_traffic_capture)
        traffic_actions.addWidget(self.traffic_capture_button)
        traffic_layout.addLayout(traffic_actions)
        self.traffic_note = QLabel("Wybierz lokalny adapter i log. To analiza historyczna, bez przechwytywania pakietów.")
        self.traffic_note.setWordWrap(True)
        traffic_layout.addWidget(self.traffic_note)
        self.traffic_table = QTableWidget(0, 4)
        self.traffic_table.setHorizontalHeaderLabels(["Czas", "Źródłowe IP", "Ocena", "Porty"])
        self.traffic_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.traffic_table.setEditTriggers(QTableWidget.NoEditTriggers)
        traffic_layout.addWidget(self.traffic_table, 1)
        tabs.addTab(traffic_card, "Ruch (NetRadar)")
        adapter_card = QFrame()
        adapter_card.setObjectName("Card")
        adapter_layout = QVBoxLayout(adapter_card)
        self.adapter_table = QTableWidget(0, 4)
        self.adapter_table.setHorizontalHeaderLabels(["Adapter", "IPv4", "Brama", "DNS IPv4"])
        self.adapter_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.adapter_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.adapter_table.setSelectionBehavior(QTableWidget.SelectRows)
        adapter_layout.addWidget(self.adapter_table)
        tabs.addTab(adapter_card, "Adaptery i DNS")
        sentinel_card = QFrame()
        sentinel_card.setObjectName("Card")
        sentinel_layout = QVBoxLayout(sentinel_card)
        sentinel_layout.addWidget(QLabel("Status z istniejącego Network Sentinel (bridge JSON v2)"))
        self.sentinel_button = QPushButton("Odczytaj status Sentinel")
        self.sentinel_button.clicked.connect(self.choose_sentinel_status)
        sentinel_layout.addWidget(self.sentinel_button)
        self.sentinel_status = QLabel("Nie odczytano statusu.")
        self.sentinel_status.setWordWrap(True)
        sentinel_layout.addWidget(self.sentinel_status)
        firewall_actions = QHBoxLayout()
        self.firewall_ip = QLineEdit()
        self.firewall_ip.setPlaceholderText("Pojedynczy IPv4 (można wybrać ze skanu)")
        firewall_actions.addWidget(self.firewall_ip)
        self.firewall_from_scan = QPushButton("Użyj zaznaczonego ze skanu")
        self.firewall_from_scan.clicked.connect(self.use_discovered_ip)
        firewall_actions.addWidget(self.firewall_from_scan)
        self.firewall_plan_button = QPushButton("Sprawdź plan blokady")
        self.firewall_plan_button.clicked.connect(lambda: self.start_firewall_change(True, False))
        firewall_actions.addWidget(self.firewall_plan_button)
        sentinel_layout.addLayout(firewall_actions)
        firewall_change_actions = QHBoxLayout()
        self.firewall_block_button = QPushButton("Zablokuj IP")
        self.firewall_block_button.clicked.connect(lambda: self.start_firewall_change(True, True))
        firewall_change_actions.addWidget(self.firewall_block_button)
        self.firewall_unblock_button = QPushButton("Cofnij blokadę IP")
        self.firewall_unblock_button.clicked.connect(lambda: self.start_firewall_change(False, True))
        firewall_change_actions.addWidget(self.firewall_unblock_button)
        sentinel_layout.addLayout(firewall_change_actions)
        self.firewall_note = QLabel("Zmiana dotyczy tylko reguł utworzonych przez nowe Network Center. Wymaga administratora.")
        self.firewall_note.setWordWrap(True)
        sentinel_layout.addWidget(self.firewall_note)
        deep_actions = QHBoxLayout()
        self.deep_interfaces = QComboBox()
        deep_actions.addWidget(self.deep_interfaces, 1)
        self.deep_refresh = QPushButton("Interfejsy TShark")
        self.deep_refresh.clicked.connect(self.refresh_deep_interfaces)
        deep_actions.addWidget(self.deep_refresh)
        self.deep_seconds = QSpinBox()
        self.deep_seconds.setRange(1, 300)
        self.deep_seconds.setValue(30)
        self.deep_seconds.setSuffix(" s")
        deep_actions.addWidget(self.deep_seconds)
        self.deep_button = QPushButton("Deep Capture")
        self.deep_button.clicked.connect(self.toggle_deep_capture)
        deep_actions.addWidget(self.deep_button)
        sentinel_layout.addLayout(deep_actions)
        self.deep_note = QLabel("TShark/Npcap: tylko metadane ARP/TCP/UDP/ICMP. Uruchom ręcznie na wybranym interfejsie.")
        self.deep_note.setWordWrap(True)
        sentinel_layout.addWidget(self.deep_note)
        self.auto_protection = QCheckBox("Automatyczna blokada po dwóch alertach HIGH (ta sesja)")
        self.auto_protection.toggled.connect(self.toggle_auto_protection)
        sentinel_layout.addWidget(self.auto_protection)
        self.deep_alerts = QPlainTextEdit()
        self.deep_alerts.setReadOnly(True)
        self.deep_alerts.setMaximumHeight(110)
        sentinel_layout.addWidget(self.deep_alerts)
        self.sentinel_events_button = QPushButton("Odczytaj ostatnie alerty")
        self.sentinel_events_button.clicked.connect(self.choose_sentinel_events)
        sentinel_layout.addWidget(self.sentinel_events_button)
        self.sentinel_events_note = QLabel("Nie odczytano alertów.")
        sentinel_layout.addWidget(self.sentinel_events_note)
        self.sentinel_events_table = QTableWidget(0, 4)
        self.sentinel_events_table.setHorizontalHeaderLabels(["Czas", "Waga", "Typ", "Źródłowe IP"])
        self.sentinel_events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sentinel_events_table.setEditTriggers(QTableWidget.NoEditTriggers)
        sentinel_layout.addWidget(self.sentinel_events_table, 1)
        tabs.addTab(sentinel_card, "Sentinel")
        history_card = QFrame()
        history_card.setObjectName("Card")
        history_layout = QVBoxLayout(history_card)
        self.history_button = QPushButton("Odczytaj historię urządzeń Sentinel")
        self.history_button.clicked.connect(self.choose_device_history)
        history_layout.addWidget(self.history_button)
        self.history_note = QLabel("Nie odczytano historii.")
        history_layout.addWidget(self.history_note)
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Czas", "Klucz", "IP", "Zdarzenie", "Szczegóły"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        history_layout.addWidget(self.history_table, 1)
        tabs.addTab(history_card, "Historia urządzeń")
        registry_card = QFrame()
        registry_card.setObjectName("Card")
        registry_layout = QVBoxLayout(registry_card)
        self.registry_button = QPushButton("Odczytaj znane i zaufane urządzenia Sentinel")
        self.registry_button.clicked.connect(self.read_sentinel_registry)
        registry_layout.addWidget(self.registry_button)
        self.registry_note = QLabel("Nie odczytano list Sentinel. Zaufanie nie oznacza obecności online.")
        self.registry_note.setWordWrap(True)
        registry_layout.addWidget(self.registry_note)
        self.registry_table = QTableWidget(0, 5)
        self.registry_table.setHorizontalHeaderLabels(["Klucz", "IP", "Nazwa", "Znane", "Zaufane"])
        self.registry_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.registry_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.registry_table.setSelectionBehavior(QTableWidget.SelectRows)
        registry_layout.addWidget(self.registry_table, 1)
        trust_actions = QHBoxLayout()
        trust_button = QPushButton("Zaufaj wybranemu")
        trust_button.clicked.connect(lambda: self.change_selected_trust(True))
        trust_actions.addWidget(trust_button)
        untrust_button = QPushButton("Usuń zaufanie")
        untrust_button.clicked.connect(lambda: self.change_selected_trust(False))
        trust_actions.addWidget(untrust_button)
        undo_trust_button = QPushButton("Cofnij z kopii")
        undo_trust_button.clicked.connect(self.undo_trust_change)
        trust_actions.addWidget(undo_trust_button)
        registry_layout.addLayout(trust_actions)
        self.registry_compare_button = QPushButton("Porównaj listy z ostatnim skanem")
        self.registry_compare_button.clicked.connect(self.compare_sentinel_devices)
        registry_layout.addWidget(self.registry_compare_button)
        report_button = QPushButton("Zapisz raport LAN HTML")
        report_button.clicked.connect(self.save_network_report)
        registry_layout.addWidget(report_button)
        self.registry_comparison = QPlainTextEdit()
        self.registry_comparison.setReadOnly(True)
        self.registry_comparison.setMaximumHeight(125)
        registry_layout.addWidget(self.registry_comparison)
        tabs.addTab(registry_card, "Zaufane urządzenia")
        main.addWidget(tabs, 1)
        self.adapter_status = QLabel("Brak odczytu adapterów.")
        self.adapter_status.setWordWrap(True)
        main.addWidget(self.adapter_status)
        self.status = QLabel("Wybierz Odśwież, aby odczytać dane.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        layout.addWidget(content, 1)
        if autoload:
            self.refresh()

    def refresh(self):
        if ((self.worker is not None and self.worker.isRunning()) or
                (self.adapter_worker is not None and self.adapter_worker.isRunning())):
            return
        self.refresh_button.setEnabled(False)
        self.neighbors_data = None
        self.adapters_data = None
        self.last_discovery_result = None
        self.report_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.status.setText("Odczytuję lokalną tablicę sąsiadów…")
        self.worker = NeighborWorker(self)
        self.worker.loaded.connect(self.show_neighbors)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.finish_refresh)
        self.adapter_worker = AdapterWorker(self)
        self.adapter_worker.loaded.connect(self.show_adapters)
        self.adapter_worker.failed.connect(self.show_adapter_error)
        self.adapter_worker.finished.connect(self.finish_refresh)
        self.worker.start()
        self.adapter_worker.start()

    def finish_refresh(self):
        if not self.worker.isRunning() and not self.adapter_worker.isRunning():
            self.refresh_button.setEnabled(True)

    def show_neighbors(self, rows):
        self.neighbors_data = rows
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, value in enumerate((
                ", ".join(row["ips"]), row["mac"], ", ".join(row["states"]),
                ", ".join(row["interfaces"]) or "Niedostępne",
            )):
                self.table.setItem(index, column, QTableWidgetItem(value))
        self.count.setText(f"{len(rows)} urządzeń w cache")
        self.status.setText("Odczyt ukończony. Dane pochodzą z cache systemu; brak wpisu nie dowodzi, że urządzenie jest offline.")
        self.update_save_state()
        if self.device_history is not None:
            self.record_local_history(rows)

    def show_error(self, message):
        self.neighbors_data = None
        self.save_button.setEnabled(False)
        self.count.setText("Dane niedostępne")
        self.table.setRowCount(0)
        self.status.setText(message)

    def show_adapters(self, rows):
        self.adapters_data = rows
        self.optimizer_adapter.clear()
        for row in rows:
            if isinstance(row.get("index"), int):
                self.optimizer_adapter.addItem(f"{row['name']} (#{row['index']})", row["index"])
        self.adapter_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, value in enumerate((
                row["name"], ", ".join(row["ipv4"]) or "Niedostępne",
                ", ".join(row["gateway"]) or "Niedostępne",
                ", ".join(row["dns"]) or "Niedostępne",
            )):
                self.adapter_table.setItem(index, column, QTableWidgetItem(value))
        self.adapter_status.setText(f"Odczytano {len(rows)} adapterów. DNS pokazuje konfigurację, nie wynik testu łączności.")
        candidates = discovery_candidates(rows)
        configured = sum("Aktualny DNS systemu/DHCP" in row["sources"] for row in candidates)
        gateways = sum("Brama — DNS niepotwierdzony" in row["sources"] for row in candidates)
        self.dns_benchmark_note.setText(
            f"Wykryto {configured} adresów DNS z adapterów i {gateways} adresów bram. "
            "Brama może nie obsługiwać DNS; benchmark nie zmienia konfiguracji.")
        self.update_save_state()

    def show_adapter_error(self, message):
        self.adapters_data = None
        self.optimizer_adapter.clear()
        self.save_button.setEnabled(False)
        self.adapter_table.setRowCount(0)
        self.adapter_status.setText(f"Adaptery: {message}")

    def update_save_state(self):
        self.save_button.setEnabled(self.neighbors_data is not None and self.adapters_data is not None)

    def show_network_repair_plan(self):
        plan = plan_repair(self.network_repair_operation.currentData())
        self.network_repair_output.setPlainText(json.dumps(plan, ensure_ascii=False, indent=2))
        self.status.setText("Plan naprawy bez wykonania. Brak gwarantowanego cofnięcia.")

    def show_network_repair_journals(self):
        directory = QFileDialog.getExistingDirectory(self, "Katalog dzienników napraw")
        if not directory:
            return
        try:
            rows = [row for row in list_repair_journals(directory)
                    if row["operation"] in ("flush-dns", "dhcp-renew", "winsock-reset")]
            self.network_repair_output.setPlainText(json.dumps(rows, ensure_ascii=False, indent=2))
            self.status.setText(f"Odczytano {len(rows)} dzienników napraw sieci.")
        except (OSError, ValueError) as error:
            self.status.setText(f"Nie odczytano dzienników: {error}")

    def start_network_repair(self):
        if self.network_repair_worker is not None and self.network_repair_worker.isRunning():
            return
        operation = self.network_repair_operation.currentData()
        plan = plan_repair(operation)
        directory = QFileDialog.getExistingDirectory(self, "Katalog na dziennik i migawkę diagnostyczną")
        if not directory:
            return
        answer = QMessageBox.question(
            self, "Naprawa sieci bez rollbacku",
            f"Uruchomić {' '.join(plan['command'])}?\n{plan['description']}\n"
            "Wymagany administrator. Przed wykonaniem powstanie dziennik i migawka diagnostyczna. "
            "Brak gwarantowanego cofnięcia. Połączenie może zostać przerwane.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.network_repair_run_button.setEnabled(False)
        self.network_repair_plan_button.setEnabled(False)
        self.network_repair_operation.setEnabled(False)
        self.status.setText(f"Wykonuję {operation}; poczekaj na zakończenie.")
        self.network_repair_worker = NetworkRepairWorker(operation, directory, self)
        self.network_repair_worker.loaded.connect(self.show_network_repair_result)
        self.network_repair_worker.failed.connect(self.show_network_repair_error)
        self.network_repair_worker.finished.connect(self.finish_network_repair)
        self.network_repair_worker.start()

    def show_network_repair_result(self, result):
        self.network_repair_output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        self.status.setText(f"Naprawa {result['operation']}: {result['status']}; dziennik: {result['journal']}")

    def show_network_repair_error(self, message):
        self.status.setText("Naprawa nie została ukończona: " + message)

    def finish_network_repair(self):
        self.network_repair_run_button.setEnabled(True)
        self.network_repair_plan_button.setEnabled(True)
        self.network_repair_operation.setEnabled(True)

    def show_help(self):
        QMessageBox.information(
            self, "Pomoc — Network Center",
            "Urządzenia pochodzą z lokalnego cache sąsiadów. Brak wpisu nie oznacza offline. "
            "Skan ICMP jest ograniczony do lokalnej podsieci /24 i nie ocenia urządzeń bez odpowiedzi jako offline. "
            "Karta Internet mierzy wskazany IP i opcjonalnie trasę oraz MTU; brak odpowiedzi ICMP nie dowodzi awarii. "
            "Karta Porty uruchamia ograniczone profile Nmap; cele poza localhost wymagają zaznaczenia zgody. "
            "Historia LAN zapisuje obserwacje MAC/IP w lokalnej bazie SQLite dopiero po włączeniu; brak wpisu cache nie oznacza offline. "
            "Optymalizacja odczytuje DNS/MTU/TCP i inne ustawienia adaptera bez ich zmiany. "
            "Naprawa sieci pokazuje plan przed wykonaniem. Flush DNS czyści cache, nie zmienia adresów DNS. "
            "Odnowienie DHCP może przerwać łączność, a reset Winsock może wymagać restartu. Brak gwarantowanego cofnięcia. "
            "Ruch analizuje wskazany log Windows/JSONL/Linux; alerty są heurystyką, a nie dowodem ataku. "
            "Adaptery i DNS pochodzą z bieżącej konfiguracji Windows; to nie jest test Internetu. "
            "Migawka zawiera lokalne adresy IP i MAC. Zapis następuje tylko po wyborze nowego pliku. "
            "Karta Sentinel czyta status JSON starego modułu; flaga running w starym pliku "
            "nie potwierdza, że proces nadal działa. Sprawdzaj czas aktualizacji. "
            "Alerty i historia urządzeń są odczytywane z istniejących logów JSONL; "
            "błędny wiersz daje UNKNOWN. Historia pokazuje obserwacje, nie potwierdza aktualnej obecności urządzenia. "
            "Deep Capture wymaga TShark/Npcap. Automatyczne reguły można włączyć tylko po pełnym odczycie listy zaufanych; "
            "dwa alerty HIGH z jednego IP uruchamiają blokadę własnymi regułami IN/OUT. "
            "Heurystyka może dać fałszywy alarm, a blokadę można cofnąć w karcie Sentinel.",
        )

    def choose_sentinel_status(self):
        local = os.environ.get("LOCALAPPDATA")
        default = (Path(local) / "PrestigeTech" / "NetworkSentinel" / "bridge" / "sentinel-status.json"
                   if local else None)
        path = str(default) if default is not None and default.is_file() else ""
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Wybierz sentinel-status.json", "", "JSON (*.json)")
        if not path:
            return
        try:
            self.show_sentinel_status(read_sentinel_status(path))
        except (OSError, ValueError, TypeError) as error:
            self.sentinel_status.setText(f"Status Sentinel niedostępny: {error}")

    def use_discovered_ip(self):
        row = self.discovery_table.currentRow()
        if row < 0 or self.discovery_table.item(row, 0) is None:
            self.firewall_note.setText("Najpierw zaznacz adres w tabeli skanu lokalnego.")
            return
        self.firewall_ip.setText(self.discovery_table.item(row, 0).text())

    def start_firewall_change(self, enable, apply):
        if self.auto_firewall_worker is not None and self.auto_firewall_worker.isRunning():
            self.firewall_note.setText("Poczekaj na zakończenie automatycznej zmiany zapory.")
            return
        if self.firewall_worker is not None and self.firewall_worker.isRunning():
            return
        address = self.firewall_ip.text().strip()
        if apply:
            action = "zablokować" if enable else "cofnąć blokadę dla"
            answer = QMessageBox.question(
                self, "Zmiana zapory Windows", f"Czy {action} adres {address}?\n"
                "Program zmieni tylko własne reguły Sentinel IN/OUT.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        for button in (self.firewall_plan_button, self.firewall_block_button,
                       self.firewall_unblock_button):
            button.setEnabled(False)
        self.firewall_note.setText("Sprawdzam reguły zapory…")
        self.firewall_worker = FirewallWorker(address, enable, apply, self)
        self.firewall_worker.loaded.connect(self.show_firewall_result)
        self.firewall_worker.failed.connect(lambda message: self.firewall_note.setText(f"Zapora: {message}"))
        self.firewall_worker.finished.connect(self.finish_firewall_change)
        self.firewall_worker.start()

    def show_firewall_result(self, result):
        self.firewall_note.setText(f"{result['status']}: {result['address']}; "
                                   f"kierunki: {', '.join(result.get('directions', result.get('changed', []))) or 'bez zmian'}.")

    def finish_firewall_change(self):
        for button in (self.firewall_plan_button, self.firewall_block_button,
                       self.firewall_unblock_button):
            button.setEnabled(True)

    def show_sentinel_status(self, data):
        freshness = "NIEAKTUALNY" if data["stale"] else "aktualny"
        reported = "tak" if data["running_reported"] else "nie"
        self.sentinel_status.setText(
            f"Raport: {freshness}, {data['timestamp']}\n"
            f"Monitoring według raportu: {reported}\n"
            f"Online: {data['online_devices']}, nowe: {data['new_devices']}, "
            f"zagrożenia: {data['threats']}, alerty: {data['alert_count']}\n"
            f"Interfejs: {data['interface'] or 'brak'}, IP: {data['ip'] or 'brak'}, "
            f"brama: {data['gateway'] or 'brak'}"
        )

    def choose_sentinel_events(self):
        local = os.environ.get("LOCALAPPDATA")
        default = (Path(local) / "PrestigeTech" / "NetworkSentinel" / "logs" / "events.jsonl"
                   if local else None)
        path = str(default) if default is not None and default.is_file() else ""
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Wybierz events.jsonl Network Sentinel", "", "JSON Lines (*.jsonl)")
        if not path:
            return
        try:
            self.show_sentinel_events(read_sentinel_events(path))
        except (OSError, ValueError) as error:
            self.sentinel_events_table.setRowCount(0)
            self.sentinel_events_note.setText(f"Alerty niedostępne: {error}")

    def show_sentinel_events(self, result):
        rows = result["events"]
        self.sentinel_events_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, value in enumerate((row["time"], row["severity"], row["type"], row["source_ip"])):
                self.sentinel_events_table.setItem(index, column, QTableWidgetItem(value))
        quality = "UNKNOWN: błędne wiersze" if result["status"] != "COMPLETE" else "Odczyt kompletny"
        self.sentinel_events_note.setText(f"{quality}; pokazano {len(rows)} alertów.")

    def choose_device_history(self):
        local = os.environ.get("LOCALAPPDATA")
        default = (Path(local) / "PrestigeTech" / "NetworkSentinel" / "logs" / "device-history.jsonl"
                   if local else None)
        path = str(default) if default is not None and default.is_file() else ""
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Wybierz device-history.jsonl Network Sentinel", "", "JSON Lines (*.jsonl)")
        if not path:
            return
        try:
            result = read_device_history(path)
        except (OSError, ValueError) as error:
            self.history_table.setRowCount(0)
            self.history_note.setText(f"Historia niedostępna: {error}")
            return
        rows = result["events"]
        self.history_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, key in enumerate(("Time", "Key", "IP", "Event", "Details")):
                self.history_table.setItem(index, column, QTableWidgetItem(row[key]))
        quality = "UNKNOWN: błędne wiersze" if result["status"] != "COMPLETE" else "Odczyt kompletny"
        self.history_note.setText(f"{quality}; pokazano {len(rows)} zdarzeń historycznych.")

    def read_sentinel_registry(self):
        self.auto_protection.setChecked(False)
        local = os.environ.get("LOCALAPPDATA")
        folder = (self.sentinel_registry_folder or
                  (Path(local) / "PrestigeTech" / "NetworkSentinel" / "database" if local else None))
        if folder is None or not folder.is_dir():
            selected = QFileDialog.getExistingDirectory(self, "Wybierz katalog database Network Sentinel")
            if not selected:
                return
            folder = Path(selected)
        try:
            result = correlate_devices(read_device_registry(folder / "known-devices.json"),
                                       read_device_registry(folder / "trusted-devices.json"))
        except (OSError, ValueError) as error:
            self.sentinel_registry_result = None
            self.auto_protection.setChecked(False)
            self.registry_table.setRowCount(0)
            self.registry_note.setText(f"Listy Sentinel niedostępne: {error}")
            return
        rows = result["devices"]
        self.sentinel_registry_folder = folder
        self.sentinel_registry_result = result
        if result["status"] != "COMPLETE":
            self.auto_protection.setChecked(False)
        self.registry_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, value in enumerate((row["key"], row["ip"], row["name"],
                                            "tak" if row["known"] else "nie",
                                            "tak" if row["trusted"] else "nie")):
                self.registry_table.setItem(index, column, QTableWidgetItem(value))
        mismatches = sum(row["ip_mismatch"] for row in rows)
        quality = "częściowy odczyt" if result["status"] != "COMPLETE" else "pełny odczyt"
        self.registry_note.setText(f"{quality}; {len(rows)} urządzeń, {mismatches} rozbieżności IP między listami. ")

    def change_selected_trust(self, enable):
        registry = self.sentinel_registry_result
        index = self.registry_table.currentRow()
        if (registry is None or registry["status"] != "COMPLETE"
                or not 0 <= index < len(registry["devices"]) or self.sentinel_registry_folder is None):
            self.registry_note.setText("Wczytaj kompletne listy i wybierz urządzenie.")
            return
        row = registry["devices"][index]
        if not row["known"]:
            self.registry_note.setText("Zaufanie można zmieniać tylko dla znanego urządzenia.")
            return
        answer = QMessageBox.question(
            self, "Lista zaufanych Sentinel",
            f"{'Dodać' if enable else 'Usunąć'} zaufanie dla {row['key']}? "
            "Przed zmianą powstanie kopia JSON. Aktywna ochrona zostanie wyłączona.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.auto_protection.setChecked(False)
        folder = self.sentinel_registry_folder
        try:
            result = change_trust(folder / "known-devices.json", folder / "trusted-devices.json",
                                  row["key"], enable)
        except (OSError, ValueError, RuntimeError) as error:
            self.registry_note.setText(f"Nie zmieniono zaufania: {error}")
            return
        self.read_sentinel_registry()
        if result["status"] == "APPLIED":
            self.registry_note.setText(f"Zmieniono zaufanie; kopia do cofnięcia: {result['backup']}")

    def undo_trust_change(self):
        if self.sentinel_registry_folder is None:
            self.registry_note.setText("Najpierw odczytaj listy Sentinel.")
            return
        backup, _ = QFileDialog.getOpenFileName(self, "Kopia zmiany zaufania", "", "JSON (*.json)")
        if not backup:
            return
        if QMessageBox.question(self, "Cofnięcie zaufania", "Przywrócić listę z kopii, jeśli nie była później zmieniana?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.auto_protection.setChecked(False)
        try:
            rollback_trust(self.sentinel_registry_folder / "trusted-devices.json", backup)
        except (OSError, ValueError, RuntimeError) as error:
            self.registry_note.setText(f"Nie cofnięto zaufania: {error}")
            return
        self.read_sentinel_registry()
        self.registry_note.setText("Przywrócono listę zaufanych z kopii.")

    def compare_sentinel_devices(self):
        try:
            result = assess_observations(self.sentinel_registry_result,
                                         self.last_discovery_result)
        except ValueError as error:
            self.registry_comparison.setPlainText(str(error))
            return
        self.registry_comparison.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))

    def save_network_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Nowy raport LAN", "network-report.html", "HTML (*.html)")
        if not path:
            return
        try:
            saved = export_network_report(self.last_discovery_result,
                                          self.sentinel_registry_result, path)
            self.registry_note.setText(f"Zapisano raport LAN: {saved}")
        except (OSError, ValueError) as error:
            self.registry_note.setText(f"Nie zapisano raportu LAN: {error}")

    def open_discovery_report(self):
        if self.last_discovery_result is None:
            return
        try:
            prefill = summarize_live_result("Network", self.last_discovery_result)
        except ValueError as error:
            self.discovery_note.setText("Nie przekazano skanu do raportu: " + str(error))
            return
        self.report_dialog = ReportDialog(self, prefill=prefill)
        self.report_dialog.show()

    def choose_discovery_oui(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz lokalną bazę OUI", "", "JSON (*.json)")
        if not path:
            return
        try:
            self.discovery_oui = load_oui(path)
        except (OSError, ValueError) as error:
            self.discovery_note.setText(f"Nie wczytano OUI: {error}")
            return
        self.discovery_note.setText(f"Wczytano {len(self.discovery_oui)} prefiksów OUI z {path}.")

    def start_discovery(self):
        if ((self.scope_worker is not None and self.scope_worker.isRunning()) or
                (self.discovery_worker is not None and self.discovery_worker.isRunning())):
            return
        self.last_discovery_result = None
        self.report_button.setEnabled(False)
        self.discovery_table.setRowCount(0)
        self.discover_button.setEnabled(False)
        self.discovery_note.setText("Wykrywam lokalne podsieci…")
        self.scope_worker = ScopeWorker(self)
        self.scope_worker.loaded.connect(self.choose_discovery_scope)
        self.scope_worker.failed.connect(self.show_discovery_error)
        self.scope_worker.start()

    def choose_discovery_scope(self, scopes):
        if not scopes:
            self.show_discovery_error("Brak prywatnego adaptera IPv4 do skanowania.")
            return
        labels = [f"{row['interface']} — {row['ip']} — {row['scope']}" for row in scopes]
        if len(scopes) == 1:
            selected = scopes[0]
        else:
            label, ok = QInputDialog.getItem(self, "Wybierz lokalny adapter", "Podsieć do skanowania:", labels, 0, False)
            if not ok:
                self.discover_button.setEnabled(True)
                self.discovery_note.setText("Skan anulowany przed rozpoczęciem.")
                return
            selected = scopes[labels.index(label)]
        self.last_discovery_scope = dict(selected)
        self.discovery_note.setText(f"Skanuję {selected['scope']} przez ICMP…")
        self.stop_discovery_button.setEnabled(True)
        self.discovery_worker = DiscoveryWorker(selected, self.discovery_oui,
                                                self.discovery_names.isChecked(),
                                                self.discovery_nmap.isChecked(), self)
        self.discovery_worker.loaded.connect(self.show_discovery)
        self.discovery_worker.failed.connect(self.show_discovery_error)
        self.discovery_worker.finished.connect(self.finish_discovery)
        self.discovery_worker.start()

    def show_discovery(self, result):
        self.last_discovery_result = result
        self.report_button.setEnabled(True)
        rows = result.get("observed", result["responsive"])
        self.discovery_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            self.discovery_table.setItem(index, 0, QTableWidgetItem(row["ip"]))
            self.discovery_table.setItem(index, 1, QTableWidgetItem(row["mac"] or "Brak w cache"))
            self.discovery_table.setItem(index, 2, QTableWidgetItem(row.get("hostname") or ""))
            self.discovery_table.setItem(index, 3, QTableWidgetItem(row.get("vendor") or ""))
            self.discovery_table.setItem(index, 4, QTableWidgetItem(row.get("evidence") or "ICMP"))
        state = "Przerwany/niepełny" if result["status"] != "COMPLETE" else "Zakończony"
        self.discovery_note.setText(
            f"{state}: {result['scope']}, sondowano {result['probed']} adresów, "
            f"odpowiedziało {len(result['responsive'])}; wpisów cache bez odpowiedzi: "
            f"{sum(row.get('evidence') == 'Cache — dostępność nieznana' for row in rows)}; "
            f"Nmap: {result.get('nmap_found', 0)}. "
            f"{result.get('nmap_error') or result['note']}"
        )
        if self.device_history is not None:
            self.record_local_history([{"mac": row["mac"], "ips": [row["ip"]]}
                                       for row in rows if row["mac"]])

    def show_discovery_error(self, message):
        self.last_discovery_result = None
        self.report_button.setEnabled(False)
        self.discovery_table.setRowCount(0)
        self.discovery_note.setText(f"Skan niedostępny: {message}")
        self.discover_button.setEnabled(True)
        self.stop_discovery_button.setEnabled(False)

    def stop_discovery(self):
        if self.discovery_worker is not None and self.discovery_worker.isRunning():
            self.discovery_worker.cancel_event.set()
            self.discovery_note.setText("Przerywam skan…")

    def finish_discovery(self):
        self.discover_button.setEnabled(True)
        self.stop_discovery_button.setEnabled(False)

    def start_discovery_schedule(self):
        scope = self.last_discovery_scope
        if scope is None:
            self.discovery_note.setText("Najpierw uruchom ręcznie skan i wybierz lokalną podsieć.")
            return
        answer = QMessageBox.question(
            self, "Harmonogram skanów LAN",
            f"Uruchamiać tylko ICMP w {scope['scope']} ({scope['interface']}) co "
            f"{self.schedule_minutes.value()} minut, maksymalnie {self.schedule_runs.value()} razy?\n"
            "Bez Nmap, bez reverse DNS i bez automatycznych blokad. "
            "Harmonogram działa tylko w tej sesji.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.scheduled_scope = dict(scope)
        self.scheduled_remaining = self.schedule_runs.value()
        self.discovery_timer.start(self.schedule_minutes.value() * 60 * 1000)
        self.discovery_note.setText(f"Harmonogram aktywny: {self.scheduled_remaining} skanów ICMP.")

    def stop_discovery_schedule(self):
        self.discovery_timer.stop()
        self.scheduled_scope = None
        self.scheduled_remaining = 0
        self.discovery_note.setText("Harmonogram skanów wyłączony.")

    def run_scheduled_discovery(self):
        if self.scheduled_scope is None or self.scheduled_remaining <= 0:
            self.stop_discovery_schedule()
            return
        if self.discovery_worker is not None and self.discovery_worker.isRunning():
            return
        try:
            current = local_scopes()
        except RuntimeError as error:
            self.stop_discovery_schedule()
            self.discovery_note.setText(f"Harmonogram zatrzymany: {error}")
            return
        if not any(all(row.get(key) == self.scheduled_scope.get(key)
                       for key in ("index", "ip", "scope")) for row in current):
            self.stop_discovery_schedule()
            self.discovery_note.setText("Harmonogram zatrzymany: interfejs lub podsieć zmieniły się.")
            return
        self.scheduled_remaining -= 1
        self.discover_button.setEnabled(False)
        self.stop_discovery_button.setEnabled(True)
        self.discovery_worker = DiscoveryWorker(self.scheduled_scope, self.discovery_oui,
                                                False, False, self)
        self.discovery_worker.loaded.connect(self.show_discovery)
        self.discovery_worker.failed.connect(self.show_discovery_error)
        self.discovery_worker.finished.connect(self.finish_discovery)
        self.discovery_worker.start()
        if self.scheduled_remaining == 0:
            self.discovery_timer.stop()
            self.scheduled_scope = None

    def start_internet_context(self):
        if self.internet_context_worker is not None and self.internet_context_worker.isRunning():
            return
        self.internet_context_button.setEnabled(False)
        self.internet_result.setText("Odczytuję lokalny kontekst bez sond zewnętrznych…")
        self.internet_context_worker = InternetContextWorker(self)
        self.internet_context_worker.loaded.connect(self.show_internet_context)
        self.internet_context_worker.failed.connect(
            lambda message: self.internet_result.setText(f"Kontekst niedostępny: {message}"))
        self.internet_context_worker.finished.connect(
            lambda: self.internet_context_button.setEnabled(True))
        self.internet_context_worker.start()

    def show_internet_context(self, result):
        self.internet_trace_output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        wifi_note = result.get("wifi", {}).get("security_note", "Brak danych o zabezpieczeniu Wi-Fi.")
        self.internet_result.setText(
            f"{result['status']}: {len(result['interfaces'])} interfejsów, "
            f"{len(result['links'])} łączy, {len(result['dns_servers'])} resolverów. "
            f"To odczyt konfiguracji, bez pomiaru połączenia. {wifi_note}")

    def start_internet_diagnostic(self):
        if self.internet_worker is not None and self.internet_worker.isRunning():
            return
        gateway = None
        if self.adapters_data:
            gateway = next((address for adapter in self.adapters_data for address in adapter["gateway"]), None)
        self.internet_result.setText("Trwa pomiar…")
        self.internet_trace_output.clear()
        self.internet_button.setEnabled(False)
        self.internet_cancel_button.setEnabled(True)
        self.internet_worker = InternetWorker(self.internet_target.text().strip(), gateway,
                                             self.internet_count.value(), self.internet_trace.isChecked(),
                                             self.internet_mtu.isChecked(), self.internet_http.isChecked(), self)
        self.internet_worker.loaded.connect(self.show_internet_diagnostic)
        self.internet_worker.failed.connect(self.show_internet_error)
        self.internet_worker.finished.connect(self.finish_internet_diagnostic)
        self.internet_worker.start()

    def start_guided_internet_diagnostic(self):
        self.tabs.setCurrentIndex(self.tabs.indexOf(self.internet_result.parentWidget()))
        self.internet_target.setText("1.1.1.1")
        self.internet_count.setValue(3)
        self.internet_trace.setChecked(False)
        self.internet_mtu.setChecked(False)
        self.internet_http.setChecked(True)
        self.internet_plan_button.setEnabled(False)
        self.start_internet_diagnostic()

    def show_guided_internet_plan(self):
        self.tabs.setCurrentIndex(self.tabs.indexOf(self.network_repair_output.parentWidget()))
        self.show_network_repair_plan()

    def show_internet_diagnostic(self, result):
        if result["status"] != "COMPLETE":
            self.internet_plan_button.setEnabled(False)
            self.internet_result.setText(f"INCOMPLETE: {result['reason']}")
            return
        self.internet_plan_button.setEnabled(True)
        internet = result["internet"]
        dns = result["dns"]
        trace = result.get("traceroute")
        mtu = result.get("mtu")
        web = result.get("web", {})
        link = result.get("link_context", {"status": "UNKNOWN"})
        self.internet_trace_output.setPlainText(trace["output"] if trace else "")
        self.internet_result.setText(
            f"Cel: {result['target']}; odpowiedzi {internet['received']}/{internet['samples']}; "
            f"średni RTT: {internet['mean_ms'] if internet['mean_ms'] is not None else 'brak'} ms; "
            f"utrata odpowiedzi: {internet['packet_loss_percent']:.1f}%. "
            f"DNS: {'OK' if dns['ok'] else 'niepowodzenie'}. "
            f"Ocena: {result['classification']['category']}. {result['classification']['reason']} "
            f"Trasa: {trace['status'] if trace else 'nie wybrano'}. "
            f"MTU: {mtu['estimated_ipv4_mtu'] if mtu else 'nie wybrano'}. "
            f"HTTP: {web.get('http', {}).get('http_status', web.get('http', {}).get('status', 'nie wybrano'))}; "
            f"HTTPS: {web.get('https', {}).get('http_status', web.get('https', {}).get('status', 'nie wybrano'))}. "
            f"Wi-Fi: {link.get('signal_percent', 'UNKNOWN')}%; "
            f"{link.get('category', link.get('reason', 'korelacja niedostępna'))}. {result['note']}"
        )

    def show_internet_error(self, message):
        self.internet_plan_button.setEnabled(False)
        self.internet_trace_output.clear()
        self.internet_result.setText(f"Pomiar niedostępny: {message}")

    def cancel_internet_diagnostic(self):
        if self.internet_worker is not None and self.internet_worker.isRunning():
            self.internet_worker.cancel_event.set()
            self.internet_result.setText("Przerywam po bieżącej sondzie…")

    def finish_internet_diagnostic(self):
        self.internet_button.setEnabled(True)
        self.internet_cancel_button.setEnabled(False)

    def use_dns_profile(self):
        profile = get_profile(self.dns_profile.currentData())
        self.dns_addresses.setText(", ".join(profile["ipv4"]))
        self.dns_benchmark_note.setText(
            f"{profile['name']}: {profile['description']} DoH: {profile['doh']}. "
            "Wstawienie adresów nie zmienia konfiguracji; użyj osobno Plan DNS.")

    def start_dns_benchmark(self):
        if self.dns_benchmark_worker is not None and self.dns_benchmark_worker.isRunning():
            return
        candidates = discovery_candidates(self.adapters_data or [])
        discovered = [row["address"] for row in candidates
                      if ((self.dns_include_system.isChecked()
                           and "Aktualny DNS systemu/DHCP" in row["sources"])
                          or (self.dns_include_gateway.isChecked()
                              and "Brama — DNS niepotwierdzony" in row["sources"]))]
        discovered_count = len(discovered)
        discovered = discovered[:8]
        public = [profile["ipv4"][0] for profile in DNS_PROFILES.values()]
        servers = list(dict.fromkeys([*discovered, *public]))
        self.dns_benchmark_button.setEnabled(False)
        self.dns_benchmark_stop.setEnabled(True)
        self.dns_benchmark_note.setText(
            f"Wysyłam zapytania DNS do {len(servers)} adresów: "
            f"{len(set(discovered) & set(servers))} z konfiguracji/bram oraz publiczne profile. "
            f"Pominięto {discovered_count - len(discovered)} dalszych adresów z adapterów.")
        self.dns_benchmark_worker = DnsBenchmarkWorker(servers, self.dns_benchmark_count.value(), self)
        self.dns_benchmark_worker.loaded.connect(self.show_dns_benchmark)
        self.dns_benchmark_worker.failed.connect(self.show_dns_benchmark_error)
        self.dns_benchmark_worker.finished.connect(self.finish_dns_benchmark)
        self.dns_benchmark_worker.start()

    def show_dns_benchmark(self, result):
        ranking = result["ranking"]
        self.dns_benchmark_output.setPlainText(json.dumps(ranking, ensure_ascii=False, indent=2))
        successful = sum(row["successful"] > 0 for row in ranking)
        self.dns_benchmark_note.setText(
            f"Odpowiedziało {successful}/{len(ranking)} resolverów. Brak odpowiedzi może oznaczać filtrację portu 53.")
        if self.dns_history is not None:
            try:
                saved = self.dns_history.record(result)
                self.dns_history_note.setText(f"Zapisano {saved['saved']} wyników do lokalnej historii DNS.")
            except (ValueError, sqlite3.Error) as error:
                self.dns_history_note.setText(f"Nie zapisano historii DNS: {error}")

    def show_dns_benchmark_error(self, message):
        self.dns_benchmark_note.setText("Benchmark nieukończony: " + message)

    def stop_dns_benchmark(self):
        if self.dns_benchmark_worker is not None and self.dns_benchmark_worker.isRunning():
            self.dns_benchmark_worker.cancel_event.set()
            self.dns_benchmark_note.setText("Przerywam po bieżącym zapytaniu…")

    def finish_dns_benchmark(self):
        self.dns_benchmark_button.setEnabled(True)
        self.dns_benchmark_stop.setEnabled(False)

    def start_dns_system(self, action):
        if self.dns_system_worker is not None and self.dns_system_worker.isRunning():
            return
        self.dns_doh_button.setEnabled(False)
        self.dns_system_button.setEnabled(False)
        self.dns_benchmark_note.setText("Odczytuję systemowy stan DNS…")
        self.dns_system_worker = DnsSystemWorker(action, self)
        self.dns_system_worker.loaded.connect(self.show_dns_system)
        self.dns_system_worker.failed.connect(
            lambda message: self.dns_benchmark_note.setText(f"DNS: {message}"))
        self.dns_system_worker.finished.connect(self.finish_dns_system)
        self.dns_system_worker.start()

    def show_dns_system(self, result):
        self.dns_benchmark_output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        self.dns_benchmark_note.setText(f"Systemowy DNS: {result['status']}.")

    def finish_dns_system(self):
        self.dns_doh_button.setEnabled(True)
        self.dns_system_button.setEnabled(True)

    def toggle_dns_history(self):
        if self.dns_history is not None:
            self.dns_history.close()
            self.dns_history = None
            self.dns_history_button.setText("Włącz lokalną historię DNS")
            self.dns_history_note.setText("Historia wyłączona. Baza pozostała na dysku.")
            return
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            self.dns_history_note.setText("Brak LOCALAPPDATA; nie utworzono bazy DNS.")
            return
        path = Path(local) / "PrestigeTech" / "NetworkCenter" / "dns-history.sqlite"
        try:
            self.dns_history = DnsHistory(path)
        except (OSError, sqlite3.Error) as error:
            self.dns_history_note.setText(f"Nie otwarto historii DNS: {error}")
            return
        self.dns_history_button.setText("Wyłącz lokalną historię DNS")
        self.dns_history_note.setText(f"Historia aktywna: {path}. Zapisuje tylko statystyki resolverów.")

    def show_dns_history(self):
        if self.dns_history is None:
            self.dns_history_note.setText("Najpierw włącz lokalną historię DNS.")
            return
        try:
            rows = self.dns_history.recent()
        except sqlite3.Error as error:
            self.dns_history_note.setText(f"Nie odczytano historii DNS: {error}")
            return
        self.dns_benchmark_output.setPlainText(json.dumps(rows, ensure_ascii=False, indent=2))
        self.dns_history_note.setText(f"Pokazano {len(rows)} ostatnich wyników resolverów.")

    def start_nmap(self):
        if self.nmap_worker is not None and self.nmap_worker.isRunning():
            return
        profile = self.nmap_profile.currentText()
        target = self.nmap_target.text().strip()
        try:
            command = plan_profile(profile, target, authorized=self.nmap_authorized.isChecked())
        except ValueError as error:
            self.nmap_note.setText(str(error))
            return
        directory = QFileDialog.getExistingDirectory(self, "Katalog nowych raportów Nmap")
        if not directory:
            return
        self.nmap_output.clear()
        self.nmap_note.setText(f"Uruchamiam: {' '.join(command)}")
        self.nmap_button.setEnabled(False)
        self.nmap_cancel_button.setEnabled(True)
        self.nmap_worker = NmapWorker(profile, target, directory, self.nmap_authorized.isChecked(), self)
        self.nmap_worker.loaded.connect(self.show_nmap)
        self.nmap_worker.failed.connect(self.show_nmap_error)
        self.nmap_worker.finished.connect(self.finish_nmap)
        self.nmap_worker.start()

    def show_nmap(self, result):
        hosts = result["hosts"]
        lines = []
        for address, row in sorted(hosts.items()):
            lines.append(f"{address}: {row['status']}")
            for port, value in sorted(row["ports"].items()):
                lines.append(f"  {port}: {value['state']}")
        self.nmap_output.setPlainText("\n".join(lines) or "Brak hostów w wyniku.")
        self.nmap_note.setText(f"Skan ukończony. XML: {result['xml']}")

    def show_nmap_error(self, message):
        self.nmap_output.clear()
        self.nmap_note.setText(f"Skan nieukończony: {message}")

    def cancel_nmap(self):
        if self.nmap_worker is not None and self.nmap_worker.isRunning():
            self.nmap_worker.cancel_event.set()
            self.nmap_note.setText("Przerywam Nmap…")

    def finish_nmap(self):
        self.nmap_button.setEnabled(True)
        self.nmap_cancel_button.setEnabled(False)

    def compare_nmap_files(self):
        first, _ = QFileDialog.getOpenFileName(self, "Wcześniejszy XML Nmap", "", "XML (*.xml)")
        if not first:
            return
        second, _ = QFileDialog.getOpenFileName(self, "Późniejszy XML Nmap", "", "XML (*.xml)")
        if not second:
            return
        try:
            comparison = compare_results(parse_xml(first), parse_xml(second))
        except (OSError, ValueError) as error:
            self.nmap_output.clear()
            self.nmap_note.setText(f"Nie porównano XML: {error}")
            return
        self.nmap_output.setPlainText("\n".join(
            f"{row['host']} {row.get('port', '')}: {row['event']}" for row in comparison["changes"]
        ) or "Brak zmian w wynikach.")
        self.nmap_note.setText(comparison["note"])

    def import_legacy_lan_history(self):
        source, _ = QFileDialog.getOpenFileName(self, "Wybierz bazę starego LAN Radar", "",
                                                "SQLite (*.sqlite *.db);;Wszystkie pliki (*)")
        if not source:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Nowy plik bazy po imporcie", "lan-import.sqlite",
                                                      "SQLite (*.sqlite *.db)")
        if not destination:
            return
        try:
            result = import_legacy_lan(source, destination)
        except (OSError, ValueError, sqlite3.Error) as error:
            self.local_history_note.setText(f"Import nieudany: {error}")
            return
        if self.device_history is not None:
            self.device_history.close()
        self.device_history = DeviceHistory(destination)
        self.local_history_button.setText("Wyłącz lokalną historię LAN")
        self.render_local_history()
        self.local_history_note.setText(
            f"Zaimportowano {result['devices']} urządzeń i {result['events']} zdarzeń do {destination}. "
            "Źródło pozostawiono bez zmian. Ta historia jest teraz aktywna.")

    def import_lan_observation(self):
        if self.device_history is None:
            self.local_history_note.setText("Najpierw włącz historię LAN lub zaimportuj starą bazę.")
            return
        source, _ = QFileDialog.getOpenFileName(self, "Obserwacja LAN z JSON", "", "JSON (*.json)")
        if not source:
            return
        try:
            rows = load_observation_json(source)
        except (OSError, ValueError) as error:
            self.local_history_note.setText(f"Nie zaimportowano obserwacji: {error}")
            return
        answer = QMessageBox.question(
            self, "Zakres obserwacji LAN",
            "Czy plik obejmuje całą skanowaną sieć? Wybierz Nie dla częściowej obserwacji. "
            "Przy pełnej brakujące urządzenia zostaną oznaczone jako niezaobserwowane, "
            "co nie dowodzi, że są offline.",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No)
        if answer == QMessageBox.Cancel:
            return
        try:
            result = self.device_history.observe(rows, complete=answer == QMessageBox.Yes)
            self.render_local_history()
        except (ValueError, sqlite3.Error) as error:
            self.local_history_note.setText(f"Nie zapisano obserwacji: {error}")
            return
        self.local_history_note.setText(
            f"Zaimportowano {result['observed']} urządzeń i {len(result['events'])} zdarzeń "
            f"({'pełna' if result['complete'] else 'częściowa'} obserwacja). Źródło pozostawiono bez zmian.")

    def toggle_local_history(self):
        if self.device_history is not None:
            self.device_history.close()
            self.device_history = None
            self.local_history_button.setText("Włącz lokalną historię LAN")
            self.local_history_note.setText("Historia wyłączona. Istniejąca baza pozostała na dysku.")
            self.local_devices_table.setRowCount(0)
            self.local_history_table.setRowCount(0)
            return
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            self.local_history_note.setText("Brak katalogu LOCALAPPDATA; nie utworzono bazy.")
            return
        path = Path(local) / "PrestigeTech" / "NetworkCenter" / "device-history.sqlite"
        try:
            self.device_history = DeviceHistory(path)
        except (OSError, sqlite3.Error) as error:
            self.local_history_note.setText(f"Nie otwarto historii: {error}")
            return
        self.local_history_button.setText("Wyłącz lokalną historię LAN")
        self.local_history_note.setText(f"Historia aktywna: {path}. Zapis obserwacji z odświeżania i skanu.")
        self.render_local_history()
        if self.neighbors_data is not None:
            self.record_local_history(self.neighbors_data)

    def record_local_history(self, rows):
        try:
            self.device_history.observe(rows, complete=False)
            self.render_local_history()
        except (ValueError, sqlite3.Error) as error:
            self.local_history_note.setText(f"Nie zapisano obserwacji: {error}")

    def render_local_history(self):
        if self.device_history is None:
            return
        devices = self.device_history.devices()
        self.local_devices_table.setRowCount(len(devices))
        for index, row in enumerate(devices):
            for column, value in enumerate((row["mac"], ", ".join(row["ips"]),
                                            row["hostname"], row["category"])):
                self.local_devices_table.setItem(index, column, QTableWidgetItem(value))
        rows = self.device_history.history()
        self.local_history_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, key in enumerate(("timestamp", "mac", "event", "details")):
                self.local_history_table.setItem(index, column, QTableWidgetItem(str(row[key])))

    def tag_selected_lan_device(self):
        if self.device_history is None:
            self.local_history_note.setText("Najpierw włącz lokalną historię LAN.")
            return
        index = self.local_devices_table.currentRow()
        if index < 0:
            self.local_history_note.setText("Wybierz urządzenie w tabeli.")
            return
        mac = self.local_devices_table.item(index, 0).text()
        category, ok = QInputDialog.getItem(self, "Kategoria urządzenia", mac,
                                             list(LAN_CATEGORIES), 0, False)
        if not ok:
            return
        try:
            self.device_history.tag_device(mac, category)
            self.render_local_history()
            self.local_history_note.setText(f"Zapisano kategorię {category} dla {mac}.")
        except (ValueError, sqlite3.Error) as error:
            self.local_history_note.setText(f"Nie zapisano kategorii: {error}")

    def start_optimizer_read(self):
        if self.optimizer_worker is not None and self.optimizer_worker.isRunning():
            return
        index = self.optimizer_adapter.currentData()
        if index is None:
            self.optimizer_note.setText("Najpierw odczytaj adaptery i wybierz interfejs.")
            return
        self.optimizer_button.setEnabled(False)
        self.optimizer_output.clear()
        self.optimizer_note.setText(f"Odczytuję interfejs #{index}…")
        self.optimizer_worker = OptimizerWorker(index, self)
        self.optimizer_worker.loaded.connect(self.show_optimizer_result)
        self.optimizer_worker.failed.connect(self.show_optimizer_error)
        self.optimizer_worker.finished.connect(lambda: self.optimizer_button.setEnabled(True))
        self.optimizer_worker.start()

    def show_optimizer_result(self, result):
        self.optimizer_output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        unknown = sum(row.get("status") != "OK" for row in result["sections"].values())
        self.optimizer_note.setText(f"Odczyt ukończony: {result['name']}; sekcje UNKNOWN: {unknown}.")

    def show_optimizer_error(self, message):
        self.optimizer_output.clear()
        self.optimizer_note.setText(f"Odczyt niedostępny: {message}")

    def start_dns_change(self, action):
        if self.dns_change_worker is not None and self.dns_change_worker.isRunning():
            return
        index = self.optimizer_adapter.currentData()
        family = self.dns_family.currentText()
        backup = None
        if action != "rollback" and index is None:
            self.optimizer_note.setText("Najpierw odczytaj adaptery i wybierz interfejs.")
            return
        if action == "rollback":
            backup, _ = QFileDialog.getOpenFileName(self, f"Wybierz kopię DNS {family}", "", "JSON (*.json)")
            if not backup:
                return
            answer = QMessageBox.question(self, "Przywrócenie DNS",
                                          f"Czy przywrócić ustawienia z kopii {backup}?\n"
                                          "Zmiana zostanie odmówiona, jeśli DNS zmieniono po utworzeniu kopii.",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
            servers = None
        else:
            raw = self.dns_addresses.text().strip()
            servers = [part.strip() for part in raw.split(",")] if raw else None
            if action == "apply":
                backup, _ = QFileDialog.getSaveFileName(self, f"Nowa kopia ustawień DNS {family}", f"dns-{family.lower()}-backup.json",
                                                         "JSON (*.json)")
                if not backup:
                    return
                description = ", ".join(servers) if servers else "automatyczne DNS"
                answer = QMessageBox.question(self, "Zmiana DNS Windows",
                                              f"Czy ustawić {description} ({family}) na interfejsie #{index}?\n"
                                              f"Kopia: {backup}\nWymaga administratora.",
                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer != QMessageBox.Yes:
                    return
        for button in (self.dns_plan_button, self.dns_apply_button, self.dns_rollback_button):
            button.setEnabled(False)
        self.dns_family.setEnabled(False)
        self.optimizer_note.setText("Sprawdzam ustawienia DNS…")
        self.dns_change_worker = DnsChangeWorker(action, index=index, servers=servers,
                                                backup=backup, family=family, parent=self)
        self.dns_change_worker.loaded.connect(self.show_dns_change_result)
        self.dns_change_worker.failed.connect(
            lambda message: self.optimizer_note.setText(f"DNS: {message}"))
        self.dns_change_worker.finished.connect(self.finish_dns_change)
        self.dns_change_worker.start()

    def show_dns_backups(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz katalog kopii DNS")
        if not folder:
            return
        try:
            rows = list_dns_backups(folder)
        except (OSError, ValueError) as error:
            self.optimizer_note.setText(f"Kopie DNS: {error}")
            return
        self.optimizer_output.setPlainText(json.dumps(rows, ensure_ascii=False, indent=2))
        self.optimizer_note.setText(f"Znaleziono {len(rows)} kopii DNS (maksymalnie 200).")

    def show_dns_change_result(self, result):
        self.optimizer_output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        self.optimizer_note.setText(f"DNS: {result['status']}.")

    def finish_dns_change(self):
        for button in (self.dns_plan_button, self.dns_apply_button, self.dns_rollback_button):
            button.setEnabled(True)
        self.dns_family.setEnabled(True)

    def start_mtu_change(self, action):
        if self.mtu_change_worker is not None and self.mtu_change_worker.isRunning():
            return
        index = self.optimizer_adapter.currentData()
        backup = target = None
        if action == "rollback":
            backup, _ = QFileDialog.getOpenFileName(self, "Wybierz kopię MTU Center", "", "JSON (*.json)")
            if not backup:
                return
            answer = QMessageBox.question(self, "Przywrócenie MTU",
                                          f"Czy przywrócić MTU z kopii {backup}?\n"
                                          "Zmiana zostanie odmówiona, jeśli MTU zmieniono później.",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        else:
            if index is None:
                self.optimizer_note.setText("Najpierw odczytaj adaptery i wybierz interfejs.")
                return
            adapter = next((row for row in (self.adapters_data or []) if row["index"] == index), None)
            default_target = next(iter(adapter["gateway"]), "") if adapter else ""
            target, ok = QInputDialog.getText(self, "Sonda DF", "IPv4 celu sondy DF (domyślnie brama):",
                                              text=default_target)
            if not ok:
                return
            target = target.strip()
            if action == "apply":
                backup, _ = QFileDialog.getSaveFileName(self, "Nowa kopia ustawień MTU", "mtu-backup.json",
                                                         "JSON (*.json)")
                if not backup:
                    return
                answer = QMessageBox.question(self, "Zmiana MTU Windows",
                                              f"Czy ustawić MTU {self.mtu_value.value()} na interfejsie #{index}?\n"
                                              f"Sonda DF: {target}\nKopia: {backup}\nWymaga administratora.",
                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer != QMessageBox.Yes:
                    return
        for button in (self.mtu_plan_button, self.mtu_apply_button, self.mtu_rollback_button):
            button.setEnabled(False)
        self.optimizer_note.setText("Sprawdzam MTU i sondę DF…")
        self.mtu_change_worker = MtuChangeWorker(action, index=index, value=self.mtu_value.value(),
                                                target=target, backup=backup, parent=self)
        self.mtu_change_worker.loaded.connect(self.show_mtu_change_result)
        self.mtu_change_worker.failed.connect(
            lambda message: self.optimizer_note.setText(f"MTU: {message}"))
        self.mtu_change_worker.finished.connect(self.finish_mtu_change)
        self.mtu_change_worker.start()

    def show_mtu_change_result(self, result):
        self.optimizer_output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        self.optimizer_note.setText(f"MTU: {result['status']}. Sonda DF jest tylko oszacowaniem ścieżki.")

    def finish_mtu_change(self):
        for button in (self.mtu_plan_button, self.mtu_apply_button, self.mtu_rollback_button):
            button.setEnabled(True)

    def choose_traffic_log(self):
        if self.traffic_worker is not None and self.traffic_worker.isRunning():
            return
        local_ips = [address for adapter in (self.adapters_data or []) for address in adapter["ipv4"]]
        if not local_ips:
            self.traffic_note.setText("Najpierw odczytaj adaptery, aby ustalić lokalne IPv4.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Log zapory lub NetRadar")
        if not path:
            return
        self.traffic_table.setRowCount(0)
        self.traffic_button.setEnabled(False)
        self.traffic_note.setText("Analizuję log…")
        self.traffic_worker = TrafficWorker(path, self.traffic_kind.currentText(),
                                            local_ips, self.traffic_offset.text().strip(), self)
        self.traffic_worker.loaded.connect(self.show_traffic_result)
        self.traffic_worker.failed.connect(self.show_traffic_error)
        self.traffic_worker.finished.connect(lambda: self.traffic_button.setEnabled(True))
        self.traffic_worker.start()

    def show_traffic_result(self, result):
        alerts = result["alerts"]
        self.traffic_table.setRowCount(len(alerts))
        for index, row in enumerate(alerts):
            for column, value in enumerate((row["timestamp"], row["source"],
                                            row["classification"], ", ".join(map(str, row["ports"])))):
                self.traffic_table.setItem(index, column, QTableWidgetItem(value))
        self.traffic_note.setText(
            f"{result['status']}: {result['records']} rekordów, {result['rejected']} odrzuconych, "
            f"{len(alerts)} alertów. {result['note']}"
        )

    def show_traffic_error(self, message):
        self.traffic_table.setRowCount(0)
        self.traffic_note.setText(f"Analiza niedostępna: {message}")

    def toggle_traffic_stream(self):
        if self.traffic_capture_worker is not None and self.traffic_capture_worker.isRunning():
            self.traffic_note.setText("Najpierw zakończ przechwytywanie TCP SYN.")
            return
        if self.traffic_stream is not None:
            self.traffic_timer.stop()
            self.traffic_stream = None
            self.traffic_stream_button.setText("Śledź rosnący log")
            self.traffic_note.setText("Śledzenie logu zatrzymane.")
            return
        if self.traffic_stream_worker is not None and self.traffic_stream_worker.isRunning():
            self.traffic_note.setText("Poczekaj na zakończenie poprzedniego odczytu logu.")
            return
        local_ips = [address for adapter in (self.adapters_data or []) for address in adapter["ipv4"]]
        if not local_ips:
            self.traffic_note.setText("Najpierw odczytaj adaptery, aby ustalić lokalne IPv4.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz rosnący log NetRadar lub zapory")
        if not path:
            return
        try:
            self.traffic_stream = TrafficStream(path, self.traffic_kind.currentText(), local_ips,
                                                utc_offset=self.traffic_offset.text().strip())
        except ValueError as error:
            self.traffic_note.setText(f"Nie rozpoczęto śledzenia: {error}")
            return
        self.traffic_table.setRowCount(0)
        self.traffic_stream_button.setText("Zatrzymaj śledzenie")
        self.traffic_note.setText("Śledzę dopisywane wiersze; to analiza logu, bez przechwytywania pakietów.")
        self.traffic_timer.start()
        self.poll_traffic_stream()

    def poll_traffic_stream(self):
        if self.traffic_stream is None:
            return
        if self.traffic_stream_worker is not None and self.traffic_stream_worker.isRunning():
            return
        self.traffic_stream_worker = TrafficStreamWorker(self.traffic_stream, self)
        self.traffic_stream_worker.loaded.connect(self.show_traffic_stream_result)
        self.traffic_stream_worker.failed.connect(self.show_traffic_stream_error)
        self.traffic_stream_worker.start()

    def show_traffic_stream_result(self, result):
        if self.traffic_stream is None:
            return
        for row in result["alerts"]:
            index = self.traffic_table.rowCount()
            if index >= 500:
                self.traffic_table.removeRow(0)
                index -= 1
            self.traffic_table.insertRow(index)
            for column, value in enumerate((row["timestamp"], row["source"],
                                            row["classification"], ", ".join(map(str, row["ports"])))):
                self.traffic_table.setItem(index, column, QTableWidgetItem(value))
        self.traffic_note.setText(
            f"{result['status']}: +{result['records']} rekordów, +{result['rejected']} błędnych, "
            f"+{len(result['alerts'])} alertów; rotacje: {result['rotations']}. {result['note']}")

    def show_traffic_stream_error(self, message):
        self.traffic_timer.stop()
        self.traffic_stream = None
        self.traffic_stream_button.setText("Śledź rosnący log")
        self.traffic_note.setText(f"Śledzenie logu zatrzymane: {message}")

    def toggle_traffic_capture(self):
        if self.traffic_capture_worker is not None and self.traffic_capture_worker.isRunning():
            self.traffic_capture_worker.cancel_event.set()
            self.traffic_note.setText("Zatrzymuję odczyt TCP SYN…")
            return
        if self.traffic_stream is not None:
            self.traffic_note.setText("Najpierw zatrzymaj śledzenie logu.")
            return
        ips = [address for adapter in (self.adapters_data or []) for address in adapter["ipv4"]]
        if not ips:
            self.traffic_note.setText("Najpierw odczytaj adaptery i lokalny adres IPv4.")
            return
        if len(ips) == 1:
            address = ips[0]
        else:
            address, ok = QInputDialog.getItem(self, "Lokalny adapter", "IPv4 do nasłuchu:", ips, 0, False)
            if not ok:
                return
        self.traffic_table.setRowCount(0)
        self.traffic_capture_button.setText("Przerwij przechwytywanie")
        self.traffic_note.setText(f"TCP SYN na {address} przez maksymalnie 30 s; wymaga administratora. "
                                  "Payload nie jest zapisywany.")
        self.traffic_capture_worker = TrafficCaptureWorker(address, parent=self)
        self.traffic_capture_worker.alert.connect(self.show_capture_alert)
        self.traffic_capture_worker.loaded.connect(self.show_capture_result)
        self.traffic_capture_worker.failed.connect(
            lambda message: self.traffic_note.setText(f"Przechwytywanie niedostępne: {message}"))
        self.traffic_capture_worker.finished.connect(
            lambda: self.traffic_capture_button.setText("TCP SYN na żywo (30 s)"))
        self.traffic_capture_worker.start()

    def show_capture_alert(self, row):
        index = self.traffic_table.rowCount()
        if index >= 500:
            self.traffic_table.removeRow(0)
            index -= 1
        self.traffic_table.insertRow(index)
        for column, value in enumerate((row["timestamp"], row["source"],
                                        row["classification"], ", ".join(map(str, row["ports"])))):
            self.traffic_table.setItem(index, column, QTableWidgetItem(value))

    def show_capture_result(self, result):
        self.traffic_note.setText(f"{result['status']}: {result['syn_events']} metadanych TCP SYN. {result['note']}")

    def refresh_deep_interfaces(self):
        try:
            interfaces = list_interfaces()
        except (OSError, RuntimeError) as error:
            self.deep_note.setText(f"Interfejsy niedostępne: {error}")
            return
        self.deep_interfaces.clear()
        for row in interfaces:
            self.deep_interfaces.addItem(f"{row['index']}. {row['label']}", row['index'])
        self.deep_note.setText(f"Dostępne interfejsy: {len(interfaces)}. Wybierz właściwy przed uruchomieniem.")

    def toggle_deep_capture(self):
        if self.deep_capture_worker is not None and self.deep_capture_worker.isRunning():
            self.deep_capture_worker.cancel_event.set()
            self.deep_note.setText("Zatrzymuję Deep Capture…")
            return
        interface = self.deep_interfaces.currentData()
        if interface is None:
            self.deep_note.setText("Najpierw pobierz i wybierz interfejs TShark.")
            return
        local_ips = [ip for adapter in (self.adapters_data or []) for ip in adapter["ipv4"]]
        if not local_ips:
            self.deep_note.setText("Najpierw odczytaj adaptery, aby odfiltrować własne IPv4.")
            return
        self.deep_alerts.clear()
        self.deep_button.setText("Zatrzymaj Deep Capture")
        self.deep_note.setText("Przechwytywanie metadanych trwa; alerty są heurystyczne.")
        self.deep_capture_worker = DeepCaptureWorker(interface, local_ips, self.deep_seconds.value(), self)
        self.deep_capture_worker.alert.connect(self.show_deep_alert)
        self.deep_capture_worker.loaded.connect(self.show_deep_result)
        self.deep_capture_worker.failed.connect(lambda message: self.deep_note.setText(f"Deep Capture niedostępny: {message}"))
        self.deep_capture_worker.finished.connect(lambda: self.deep_button.setText("Deep Capture"))
        self.deep_capture_worker.start()

    def toggle_auto_protection(self, enabled):
        if not enabled:
            self.protection_policy = None
            return
        registry = self.sentinel_registry_result
        if registry is None or registry["status"] != "COMPLETE":
            self.deep_note.setText("Najpierw odczytaj kompletne listy znanych i zaufanych urządzeń Sentinel.")
            self.auto_protection.setChecked(False)
            return
        local_ips = [ip for adapter in (self.adapters_data or []) for ip in adapter["ipv4"]]
        if not local_ips:
            self.deep_note.setText("Najpierw odczytaj lokalne adaptery IPv4.")
            self.auto_protection.setChecked(False)
            return
        answer = QMessageBox.question(
            self, "Automatyczne reguły Sentinel",
            "W tej sesji dwa oddzielne alerty HIGH z jednego IPv4 mogą utworzyć reguły blokady IN/OUT. "
            "Limit: 5 adresów. Fałszywy alarm może przerwać połączenie; cofnięcie jest w karcie Sentinel. Włączyć?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            self.auto_protection.setChecked(False)
            return
        trusted = [ip for row in registry["devices"] if row["trusted"]
                   for ip in (row["ip"], row["trusted_ip"]) if ip]
        try:
            self.protection_policy = ProtectionPolicy(trusted=trusted, local=local_ips)
        except ValueError as error:
            self.auto_protection.setChecked(False)
            self.deep_note.setText(f"Nie włączono ochrony: {error}")
            return
        self.deep_note.setText("Automatyczna ochrona włączona tylko na czas tej sesji; maksimum 5 adresów.")

    def show_deep_alert(self, alert):
        self.deep_alerts.appendPlainText(f"{alert['severity']} · {alert['source']} · {alert['category']} · {alert['attempts']}")
        if self.protection_policy is None:
            return
        try:
            decision = self.protection_policy.consider(alert)
        except ValueError:
            self.deep_note.setText("Pominięto nieprawidłowy alert ochrony.")
            return
        if decision["status"] != "BLOCK":
            return
        address = decision["address"]
        if self.auto_firewall_worker is not None and self.auto_firewall_worker.isRunning():
            self.protection_policy.release(address)
            self.deep_note.setText("Zapora jest zajęta; pominięto automatyczną blokadę.")
            return
        if self.firewall_worker is not None and self.firewall_worker.isRunning():
            self.protection_policy.release(address)
            self.deep_note.setText("Ręczna zmiana zapory trwa; pominięto automatyczną blokadę.")
            return
        self.auto_firewall_address = address
        self.auto_firewall_worker = FirewallWorker(address, True, True, self)
        self.auto_firewall_worker.loaded.connect(
            lambda result: self.deep_note.setText(f"Automatyczna ochrona: {result['status']} {result['address']}"))
        self.auto_firewall_worker.failed.connect(self.show_auto_firewall_error)
        self.auto_firewall_worker.start()

    def show_auto_firewall_error(self, message):
        if self.protection_policy is not None and self.auto_firewall_address:
            self.protection_policy.release(self.auto_firewall_address)
        self.deep_note.setText(f"Automatyczna blokada nieudana: {message}")

    def show_deep_result(self, result):
        self.deep_note.setText(f"{result['status']}: {result['packets']} metadanych, "
                               f"{len(result['alerts'])} alertów, {result['rejected']} błędnych wierszy. "
                               f"{result['note']}")

    def save_current_snapshot(self):
        if self.neighbors_data is None or self.adapters_data is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz migawkę sieci", "network-snapshot.json", "JSON (*.json)")
        if not path:
            return
        try:
            save_snapshot(make_snapshot(neighbors=self.neighbors_data,
                                        adapters=self.adapters_data,
                                        discovery=self.last_discovery_result), path)
        except (FileExistsError, OSError, ValueError) as error:
            QMessageBox.warning(self, "Nie zapisano migawki", str(error))
            return
        self.status.setText(f"Migawka zapisana: {path}")

    def save_imported_snapshot(self):
        source, _ = QFileDialog.getOpenFileName(self, "Wybierz listę urządzeń LAN", "", "JSON (*.json)")
        if not source:
            return
        try:
            snapshot = snapshot_from_json_list(source)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Nie odczytano listy LAN", str(error))
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, "Zapisz nową migawkę", "network-snapshot-import.json", "JSON (*.json)")
        if not destination:
            return
        try:
            save_snapshot(snapshot, destination)
        except (FileExistsError, OSError) as error:
            QMessageBox.warning(self, "Nie zapisano migawki", str(error))
            return
        self.status.setText(f"Migawka z {len(snapshot['neighbors'])} urządzeń zapisana: {destination}")

    def choose_snapshots_to_compare(self):
        before_path, _ = QFileDialog.getOpenFileName(self, "Wybierz wcześniejszą migawkę", "", "JSON (*.json)")
        if not before_path:
            return
        after_path, _ = QFileDialog.getOpenFileName(self, "Wybierz późniejszą migawkę", "", "JSON (*.json)")
        if not after_path:
            return
        try:
            before = json.loads(Path(before_path).read_text(encoding="utf-8"))
            after = json.loads(Path(after_path).read_text(encoding="utf-8"))
            if not isinstance(before, dict) or not isinstance(after, dict):
                raise ValueError("Nieprawidłowy format migawki.")
            result = compare_snapshots(before, after)
        except (OSError, ValueError, TypeError, KeyError) as error:
            QMessageBox.warning(self, "Nie porównano migawek", str(error))
            return
        QMessageBox.information(
            self, "Porównanie migawek",
            f"Nowo zaobserwowane: {len(result['newly_observed'])}\n"
            f"Teraz niezaobserwowane: {len(result['not_observed_now'])}\n"
            f"Zmiany IP: {len(result['changed_ips'])}\n"
            f"Zmiany nazw: {len(result['changed_hostnames'])}\n"
            f"Zmiany producenta: {len(result['changed_vendors'])}\n\n{result['note']}",
        )

    def closeEvent(self, event):
        self.discovery_timer.stop()
        self.traffic_timer.stop()
        if self.deep_capture_worker is not None and self.deep_capture_worker.isRunning():
            self.deep_capture_worker.cancel_event.set()
            self.deep_capture_worker.wait(7000)
            if self.deep_capture_worker.isRunning():
                event.ignore()
                return
        if self.auto_firewall_worker is not None and self.auto_firewall_worker.isRunning():
            self.auto_firewall_worker.wait(11000)
            if self.auto_firewall_worker.isRunning():
                event.ignore()
                return
        if self.traffic_capture_worker is not None and self.traffic_capture_worker.isRunning():
            self.traffic_capture_worker.cancel_event.set()
            self.traffic_capture_worker.wait(5000)
            if self.traffic_capture_worker.isRunning():
                event.ignore()
                return
        # Odczyt systemowy ma 10-sekundowy limit. Nie niszcz wątku w trakcie pracy.
        if self.discovery_worker is not None and self.discovery_worker.isRunning():
            self.discovery_worker.cancel_event.set()
            self.discovery_worker.wait(5000)
        if self.internet_worker is not None and self.internet_worker.isRunning():
            self.internet_worker.cancel_event.set()
            self.internet_worker.wait()
        if self.nmap_worker is not None and self.nmap_worker.isRunning():
            self.nmap_worker.cancel_event.set()
            self.nmap_worker.wait()
        if self.dns_benchmark_worker is not None and self.dns_benchmark_worker.isRunning():
            self.dns_benchmark_worker.cancel_event.set()
            self.dns_benchmark_worker.wait(3000)
            if self.dns_benchmark_worker.isRunning():
                event.ignore()
                return
        if self.device_history is not None:
            self.device_history.close()
            self.device_history = None
        if self.dns_history is not None:
            self.dns_history.close()
            self.dns_history = None
        for worker in (self.worker, self.adapter_worker, self.scope_worker,
                       self.optimizer_worker, self.traffic_worker,
                       self.traffic_stream_worker, self.firewall_worker,
                       self.internet_context_worker, self.dns_change_worker,
                       self.mtu_change_worker, self.dns_system_worker,
                       self.network_repair_worker):
            if worker is not None and worker.isRunning():
                self.refresh_button.setEnabled(False)
                worker.wait(11000)
                if worker.isRunning():
                    event.ignore()
                    self.firewall_note.setText("Poczekaj na zakończenie operacji przed zamknięciem okna.")
                    return
        super().closeEvent(event)
