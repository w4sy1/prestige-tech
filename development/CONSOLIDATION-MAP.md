# Konsolidacja Prestige Tech — inwentaryzacja 2026-09-26

Źródło: lokalne repozytoria `prestige-*`, ich `metadata.json`, pliki backendów,
Dashboard `modules.json` i istniejący status projektu. To stan kodu, nie lista
funkcji potwierdzonych na sprzęcie. `MOVE` oznacza plan migracji, nie wykonanie.
Stare repozytoria i wydania pozostają czynne do przejścia testów nowych centrów.

## Stan architektury

- 26 dotychczasowych samodzielnych programów ma własne repozytoria. Dashboard
  ma osobną gałąź `dashboard-v1` i istniejące komponenty PySide6 w `ui/`.
- DNS Benchmark rozwinął się lokalnie do DNS Center `0.4.2-dev` w tym samym
  repozytorium. Dashboard nadal wskazuje `prestige-dns-benchmark.exe`.
- `prestige-lan-radar/discovery.py` i `prestige-network-snapshot/discovery.py`
  są identyczne bitowo; to samo dotyczy ich `hosts.py`.
- `runtime.py` jest skopiowany do wielu programów (np. Hash Checker, File
  Inspector, Backup). Kopiowane są też `pdf_export.py`, `gui.py` i zasoby.
  Dotychczasowa niezależność EXE tłumaczy część duplikacji; nowy Core wymaga
  jawnego pakowania wspólnych zależności w każdym Center.
- Network Sentinel istnieje w Dashboardzie jako skrypt
  `tools/network-sentinel/NetworkSentinel.ps1`; nie ma obecnie osobnego repo.
- Prestige Distant, iDiagnostics i Registry Tool nie zostały znalezione jako
  samodzielne repozytoria w tym katalogu. Przed migracją trzeba ustalić ich
  faktyczne źródła i możliwości. Termux Setup repo nadal istnieje, choć nowy
  plan wskazuje wycofanie produktu; żadna funkcja nie została tu usunięta.
- Lokalne kopie `prestige-dns-benchmark-BACKUP-*` są backupami, a nie dodatkowymi
  modułami. Nie należy ich skanować jako źródeł produkcyjnych.

## Macierz migracji

`KEEP`: zachować działającą implementację; `MERGE`: scalić funkcję;
`MOVE`: przenieść interfejs do Center; `REFACTOR`: wydzielić wspólną usługę;
`DEPRECATE`: dopiero po testach nowego odpowiednika. Brak decyzji `REMOVE`.

| Stary moduł | Funkcja / implementacja | Zależności | Odpowiednik / duplikat | Nowy Center / sekcja | Decyzja |
|---|---|---|---|---|---|
| DNS Benchmark / Center | UDP/TCP benchmark `app.py`, konfiguracja i backup `dns_config.py` | Windows PowerShell, sieć | DNS w Internet Diagnostic, Network Optimizer | Network / DNS | KEEP, MOVE, MERGE |
| Network Optimizer | DNS/MTU, pomiar, rollback `app.py` | Windows, uprawnienia | DNS Center | Network / Optimization | KEEP, MERGE |
| Internet Diagnostic | ping, DNS, trasa, MTU `app.py`, `context.py` | systemowe narzędzia sieciowe | DNS Center, Network Snapshot | Network / Internet | KEEP, MERGE |
| LAN Radar | wykrywanie LAN, IP/MAC, historia `discovery.py`, `hosts.py` | ICMP, ARP, SQLite | Network Snapshot — identyczne pliki | Network / Devices | KEEP, REFACTOR, MOVE |
| NetRadar | firewall logs, SYN capture, alerty `capture.py`, `streaming.py` | Npcap lub logi Windows | Network Sentinel | Network / Traffic, Sentinel | KEEP, MERGE |
| Network Snapshot | sąsiedzi i porównanie `app.py`, `discovery.py`, `hosts.py` | ICMP, ARP | LAN Radar — identyczne pliki | Network / History | KEEP, REFACTOR, MOVE |
| Nmap Profiles | profile i analiza wyników `app.py` | Nmap | LAN Radar, NetRadar — porty | Network / Nmap & Ports | KEEP, MOVE |
| DNS Benchmark i Network Sentinel w Dashboardzie | kafel EXE i skrypt `NetworkSentinel.ps1` | instalacja Dashboardu | Network Center | Network / DNS, Sentinel | REFACTOR po integracji |
| ADB Diagnostic | urządzenie, usługi, sieć, logcat `app.py`, `parsers.py` | ADB | Android Inspector | Android / ADB, Diagnostics | KEEP, MERGE |
| Android Inspector | aplikacje, uprawnienia `app.py`, `access.py` | ADB | ADB Diagnostic | Android / Apps, Permissions | KEEP, MERGE |
| Security Check | scoring i reguły `app.py`, `rules.py` | Windows API / PowerShell | Malware Triage | Security / Security Checks | KEEP, MERGE |
| Malware Triage | procesy, persistence, pliki, GPU `app.py`, `rules.py`, `filescan.py` | Windows, PowerShell | Security Check, File Inspector | Security / Malware, Processes | KEEP, MERGE |
| File Inspector | hashe, typ, entropia, PE `app.py` | PowerShell opcjonalnie | Hash Checker, Malware Triage | Security / File Analysis | KEEP, REFACTOR, MOVE |
| Windows Toolkit | diagnostyka i naprawy `prestige.ps1` | PowerShell 7, Windows | System Snapshot, PC Cleanup | System / Diagnostics, Repair | KEEP, MERGE |
| PC Cleanup | kwarantanna i przywracanie `app.py` | Windows / filesystem | Windows Toolkit cleanup | System / Cleanup | KEEP, MOVE |
| System Snapshot | kolekcja stanu `app.py` | Windows | Windows Toolkit, Security Check | System / Snapshots | KEEP, MERGE |
| Repair Report | formularz i eksport `app.py` | ReportLab opcjonalnie | eksporty wszystkich modułów | Shared ReportService / Reports | KEEP, REFACTOR |
| Backup | backup, restore, ACL/VSS `app.py`, `service.py`, `acl.py`, `vss.py` | Windows VSS/admin opcjonalnie | USB Toolkit, Integrity Monitor | Storage & Recovery / Backup, Restore | KEEP, MERGE |
| USB Toolkit | nośniki, wersjonowanie, rollback `app.py`, `update.py` | Windows USB | Backup | Storage & Recovery / USB Devices | KEEP, MOVE |
| Folder Watch | snapshot, zmiany `app.py`, `native.py` | filesystem | Integrity Monitor | Monitor / Live Events | KEEP, MERGE |
| Integrity Monitor | baseline, porównanie, ACL/ADS `app.py`, `extended.py` | filesystem, Windows ACL/ADS | Folder Watch, Hash Checker | Monitor / Integrity, Baseline | KEEP, MERGE |
| Hash Checker | SHA i manifest `app.py`, podpisy `signing.py` | cryptography opcjonalnie | Integrity Monitor, File Inspector | Monitor / Hashes | KEEP, REFACTOR, MOVE |
| Termux Setup | konfiguracja i backup `configuration.py` | Android/Termux | Termux Toolkit | Termux Toolkit / Setup | MERGE, później DEPRECATE |
| Termux Toolkit | narzędzia Termux `app.py` | Termux, Android | Termux Setup | osobny Termux Toolkit | KEEP, MERGE |
| AI Diagnostic Assistant | normalizacja, reguły, API `normalization.py`, `providers.py`, `rules.py` | zewnętrzne AI opcjonalnie | raporty/analiza centrów | Shared analysis, opcjonalnie | KEEP, REFACTOR |
| Tech CLI | launcher i polecenia `app.py` | pozostałe narzędzia | Dashboard | wspólny CLI | KEEP, REFACTOR |
| Tech Dashboard | launcher, instalacja, aktualizacje, UI `ui/`, `module_manager.py` | PySide6, opcjonalne EXE | wszystkie Centra | główny Dashboard | KEEP, REFACTOR |

## Kolejność i granice zmian

1. Wspólny Core jako osobny pakiet w repo `prestige-tech`; ma mieć testy i
   kontrakty wejścia/wyjścia. Nowe Centra pobierają go jako zależność przy
   budowaniu EXE. Legacy działa dalej niezależnie.
2. Network Center: najpierw jedna implementacja wykrywania LAN, potem DNS,
   diagnostyka i porty. Ujednolicenie nazw nie zmienia jeszcze repo DNS.
3. Monitor: jeden przebieg skanowania i hash SHA-256, potem baseline/alerty.
4. System, Security, Android, Storage & Recovery; raporty integrować w miarę
   dojrzewania każdego Center. Distant dopiero po znalezieniu kodu i audycie
   bezpieczeństwa. Termux Toolkit dopiero po sprawdzeniu parytetu Setup.
5. Dashboard przełącza kafel na Center dopiero po działającym GUI, smoke teście,
   teście backendu, EXE i sprawdzeniu brakujących zależności. Stare narzędzia
   przechodzą do legacy po potwierdzeniu parytetu, bez kasowania historii.

Wizualnie bazą są istniejące `prestige-tech-dashboard/ui/theme.py` i `widgets.py`.
Przyszłe Centra PySide6 powinny korzystać ze wspólnej palety i kontrolek oraz
pokazywać wyłącznie odczyty backendów; brak odczytu oznacza `Niedostępne`.
Makiet referencyjnych nie znaleziono w repo jako jednoznacznie oznaczonych plików.
