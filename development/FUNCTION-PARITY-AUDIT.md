# Audyt parytetu funkcji — 2026-09-28

Ten plik śledzi przeniesienie funkcji starego kodu do Centrów. `Kod` oznacza
odpowiednik w nowym repozytorium, nie gotowość EXE ani test na sprzęcie.
Starych repozytoriów nie należy usuwać, dopóki wszystkie wiersze wszystkich
programów nie mają potwierdzonego parytetu i testu docelowego.

## Backup → Storage & Recovery

Źródło: `w4sy1/prestige-backup` (`app.py`, `service.py`, `acl.py`, `vss.py`).
Odpowiednik: `prestige_core/backup/` i `prestige_storage/gui.py`.

| Funkcja starego programu | Kod w Center | GUI Center | Potwierdzenie |
|---|---|---|---|
| Plan i filtr sekretów | Tak | Podgląd przed kopią | Fixture |
| Kopia wielu folderów z manifestem i SHA-256 | Tak | Tak | Fixture; duża kopia niezweryfikowana |
| Weryfikacja kopii i odmowa restore przy uszkodzeniu | Tak | Tak | Fixture |
| Restore do nowego katalogu i dziennik | Tak | Tak | Fixture; przerwanie sprawdzone testem legacy |
| Foldery standardowe Windows | `known_folders()` | Pola wyboru Pulpit/Dokumenty/Obrazy/Pobrane, łączone z ręcznym wyborem bez duplikatów | Fixture GUI; lokalny odczyt 4/4 katalogów PASS |
| Eksport systemu, sterowników i zakładek wielu przeglądarek | Tak | Opcje i wybór wielu plików zakładek; eksport może być jedyną zawartością kopii | Fixture zakładek z weryfikacją manifestu; prawdziwy eksport Windows niezweryfikowany |
| ACL przy kopii i restore | Tak | Opcja ACL | Fixture; zapis ACL Windows niezweryfikowany |
| VSS i usuwanie pozostałych migawek z dziennika | Tak | Opcja VSS i wybór dziennika | Fixture; realny VSS/admin niezweryfikowany |

Stare 29 testów zaadaptowane do nowych importów przeszły. Backend zachowuje
stary format manifestu. Parytet UX i przypadki sprzętowe pozostają otwarte.

## USB Toolkit → Storage & Recovery

Źródło: `w4sy1/prestige-usb-toolkit` (`app.py`, `update.py`).
Odpowiednik: `prestige_core/usb/` i `prestige_storage/gui.py`.

| Funkcja starego programu | Kod w Center | GUI Center | Potwierdzenie |
|---|---|---|---|
| Plan przygotowania PrestigeUSB bez zapisu | Tak; Center dodatkowo waliduje wersje i cel | Potwierdzenie z listą wersji | Fixture; plan nie tworzy katalogu |
| Przygotowanie PrestigeUSB z wieloma narzędziami | Tak | Tak | Fixture |
| Manifest i weryfikacja zestawu | Tak | Tak | Fixture |
| Aktualizacja wielu narzędzi z zachowaniem danych | Tak | Tak | Fixture |
| Rollback wersji i odmowa przy zmienionych plikach | Tak | Tak | Fixture; nośnik fizyczny niezweryfikowany |

Stare 16 testów zaadaptowane do nowych importów przeszły. Nie sprawdzono
rzeczywistego USB, utraty połączenia ani instalacyjnego EXE.

## Hash Checker → Monitor

Źródło: `w4sy1/prestige-hash-checker` (`app.py`, `signing.py`).
Odpowiednik: `prestige_core/hash_manifest.py`, `prestige_core/baseline_signing.py`
i `prestige_monitor/gui.py`.

| Funkcja starego programu | Kod/GUI Center | Potwierdzenie |
|---|---|---|
| Hash pliku SHA-256/SHA-512/SHA-1/MD5 | Tak | Fixture |
| Generowanie i weryfikacja manifestu folderu | Tak | Fixture |
| Porównanie dwóch manifestów | Tak | Fixture; stary format czytany |
| Porównanie dwóch folderów | Tak | Fixture; GUI smoke |
| Klucze, podpis i weryfikacja podpisu | Tak | Fixture; tożsamość właściciela klucza pozostaje poza zakresem |

Manifesty i podpisy przeszły test zgodności w obie strony: stary plik
weryfikuje nowe Centrum i odwrotnie. Stare osobne repozytorium usunięto z
GitHuba; pełna historia Git ma lokalny bundle, a stary EXE pozostał w
wydaniu głównego repo. Dashboard nadal pokazuje Hash Checker i potrafi
uruchomić lokalnie zainstalowany stary EXE. Nowy EXE Monitora nie został
jeszcze przetestowany.

## Integrity Monitor → Monitor

Źródło: `w4sy1/prestige-integrity-monitor` (`app.py`, `extended.py`).
Odpowiednik: `prestige_core/file_snapshot.py`, `prestige_core/baseline_update.py`,
`prestige_core/legacy_integrity.py`, `prestige_monitor/gui.py`.

| Funkcja starego programu | Kod/GUI Center | Potwierdzenie |
|---|---|---|
| Baseline SHA-256 i porównanie zmian | Tak | Fixture; niepełny skan oznaczany UNKNOWN |
| ACL/ADS i tryb POSIX | Tak, z kontrolą kompletności | Fixture; prawdziwe ograniczone konto Windows niezweryfikowane |
| Aktualizacja baseline z kopią poprzedniej wersji | Tak | Fixture; stary plik nie jest nadpisywany przy imporcie |
| Odczyt starego formatu baseline | Nowa kopia w formacie Center po walidacji | Fixture zgodności i odmowy dla `../` |
| Klucze, podpis i weryfikacja podpisu | Tak | Fixture; zaufanie do właściciela klucza poza zakresem |

Import nie podnosi niepełnego starego baseline do stanu `complete`. Nie
sprawdzono jeszcze dużych drzew i metadanych ACL/ADS na ograniczonym koncie.

## Folder Watch → Monitor

Źródło: `w4sy1/prestige-folder-watch` (`app.py`, `native.py`).
Odpowiednik: `prestige_core/watch_state.py`, `watch_state_import.py`,
`native_events.py` oraz `prestige_monitor/gui.py`.

| Funkcja starego programu | Kod/GUI Center | Potwierdzenie |
|---|---|---|
| Skan i wykrywanie create/modify/delete/rename | Tak | Fixture i smoke GUI; duże drzewo niezweryfikowane |
| Polling z trwałą bazą SQLite | Tak | Fixture; wznowienie po restarcie z ponownym hashowaniem |
| Import starej bazy polling | Tak, do nowego pliku | Fixture; oryginał bez zmian |
| Natywne zdarzenia FileSystemWatcher | Tak | Lokalny Windows i smoke GUI; overflow wymaga testu obciążenia |
| Import starej bazy native bez tabeli `state` | Tak, tylko historia zdarzeń | Fixture; baseline powstaje przy pierwszym skanie |

Stary tryb native zapisywał historię, lecz nie tworzył migawki. Import nie
traktuje braku migawki jako kompletnego skanu. Zdarzenia natywne nowego
Monitora nie aktualizują automatycznie bazy polling; trzeba je zapisać
osobno w historii JSONL.

## Network Snapshot → Network Center

Źródło: `w4sy1/prestige-network-snapshot` (`app.py`, `hosts.py`,
`discovery.py`). Odpowiednik: `prestige_core/network_snapshot.py`, funkcje
odkrywania LAN i `prestige_network_center/gui.py`.

| Funkcja starego programu | Kod/GUI Center | Potwierdzenie |
|---|---|---|
| Zapis nowej migawki bez nadpisania poprzedniej | Tak | Fixture |
| Porównanie dwóch migawek i oznaczenie braku obserwacji | Tak | Fixture; brak urządzenia nie jest dowodem offline |
| Odczyt starego formatu `hosts` | Tak | Fixture |
| Scalenie IP tego samego MAC i formatów `aa-bb`/`aa:bb` | Tak | Fixture zgodności |
| Jawne discovery / import listy i OUI | Częściowe odpowiedniki w Network Center | Realny skan i pełny parytet komend pozostają otwarte |

Nowe porównanie normalizuje IP i MAC bez zmiany zapisanych migawek. Nie
potwierdzono jeszcze parytetu danych `discovery` ze starej migawki ani
wszystkich parametrów starego CLI.

## System Snapshot, Security Check, Repair Report i PC Cleanup → Centra

| Stare repozytorium i funkcje | Odpowiednik w Center | Potwierdzenie |
|---|---|---|
| System Snapshot: 12 sekcji Windows, zapis i porównanie offline z identyfikacją zmian | `prestige_core/system_snapshot.py`, System Center | 14 testów starego repo i testy Center PASS; lokalny odczyt 12/12 sekcji |
| Security Check: 21 kontroli, analiza reguł i odczyt pliku JSON | `prestige_core/security_check.py`, `security_rules.py`, Security Center | 19 testów starego repo i testy Center PASS; lokalnie 4 sekcje UNKNOWN |
| Repair Report: szablon, walidacja, HTML/JSON/TXT | `prestige_core/report_service.py`, Report Center | 11 testów starego repo i testy Center PASS; dodatkowo PDF |
| PC Cleanup: profile, skan, plan, kwarantanna i przywrócenie | `prestige_core/pc_cleanup.py`, System Center | 17 testów starego repo i fixture Center PASS; prawdziwego czyszczenia nie wykonano |

Po potwierdzeniu odpowiedników kodowych usunięto cztery osobne repozytoria
z GitHuba. Każde ma zweryfikowany pełny bundle historii Git w lokalnym
`C:\Users\01dwa\.codex\backups\prestige-tech-legacy`. Ich stare EXE pozostają
w wydaniu zbiorczym i w katalogu Dashboardu obok Centrów. Nowe EXE Centrów
oraz integracja Repair Report ze wszystkimi Centrami nie są zweryfikowane.

Pozostałe programy są nadal opisane na poziomie modułów w
`CENTER-MIGRATION-MATRIX.md`; wymagają audytu komend i zachowań w tym samym
formacie przed decyzją o usunięciu starych repozytoriów.

## File Inspector → Security Center

Źródło: `w4sy1/prestige-file-inspector` (`app.py`, `runtime.py`, `pdf_export.py`).
Odpowiednik: `prestige_core/file_inspector.py`, `prestige_security/gui.py`.

| Funkcja starego programu | Kod/GUI Center | Potwierdzenie |
|---|---|---|
| Odczyt pliku bez wykonania, metadane, magic, PE, entropia | Tak | Fixture starego i nowego kodu PASS |
| SHA-256/512, SHA-1/MD5 podczas tego samego odczytu | Tak | Test pojedynczego otwarcia i hash PASS |
| Ciągi znaków tylko po zgodzie | Tak | Test starego i nowego kodu oraz opcja GUI PASS |
| Status podpisu Authenticode | Tak w kodzie | Podpisanego pliku Windows nie zweryfikowano |
| Samodzielne CLI, eksport JSON/TXT/HTML i PDF | Nie jako samodzielna komenda File Inspector Center | Stare repo nadal potrzebne |

Osobne repozytorium File Inspector pozostaje. Nie stwierdzono pełnego
parytetu sposobu uruchamiania i eksportu; nowych EXE również nie sprawdzono.
