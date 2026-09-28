# Migracja modułów do Centrów — stan 2026-09-28

`Częściowy` oznacza tylko wymieniony, przetestowany wycinek. Hash Checker ma
potwierdzony parytet funkcji w kodzie i zarchiwizowane stare repozytorium;
pozostałe Centra nie zastępują jeszcze starych programów. `Nie` w kolumnie
EXE oznacza brak
**zweryfikowanego EXE nowego Center**, nie stan opublikowanego starego EXE.
Szczegółowy audyt komend Backup, USB Toolkit i Hash Checker jest w
`FUNCTION-PARITY-AUDIT.md`.
Dashboard nadal pokazuje stare moduły. Jego manifest zawiera także 10 nowych
Centrów uruchamianych z sąsiedniego repozytorium `prestige-tech`; wygląd
Dashboardu pozostał bez zmian. Kolumna `Legacy` poniżej oznacza, że stary
program nadal ma własną pozycję, a nie brak pozycji nowego Center.

| Stary moduł | Center / sekcja | Status nowego odpowiednika | Test nowego odpowiednika | EXE Center | Dashboard |
|---|---|---|---|---|---|
| DNS Benchmark / DNS Center | Network / DNS | Profile publicznych resolverów, pomiar UDP/TCP, ranking i przerwanie w Core/GUI; pełny parytet starego DNS Center do audytu | Fixture/GUI PASS; rzeczywistych resolverów nie testowano | Nie | Legacy |
| Network Optimizer | Network / Optymalizacja | Odczyt DNS/MTU/TCP/zasilania/powiązań/cache oraz zmiany DNS IPv4 i MTU 576–1500 z nową kopią JSON, weryfikacją i warunkowym cofnięciem w Core/GUI | Fixture DNS/MTU i lokalne plany PASS; zapis/cofnięcie w VM niezweryfikowane, jumbo MTU poza zakresem | Nie | Legacy |
| Internet Diagnostic | Network / Internet | ICMP/DNS, opcjonalna trasa i MTU oraz lokalny kontekst DHCP/interfejsów/tras/DNS/Wi-Fi; wynik ma korelację z sygnałem i bramą, z zaznaczeniem niepewności | Fixture/GUI i lokalny odczyt kontekstu PASS; wcześniejsze 2 próbki ICMP do 1.1.1.1 i DNS PASS | Nie | Legacy |
| LAN Radar | Network / Urządzenia | Cache, adaptery, ograniczony skan ICMP, opcjonalny reverse DNS i lokalna baza OUI, opt-in historia SQLite, import starej bazy do nowego pliku oraz tagowanie urządzeń; pełny parytet nadal brak | Core/GUI fixture PASS; realny skan własnego Wi-Fi /24: 253 sondy, 1 odpowiedź, 0 błędów sond | Nie | Legacy |
| NetRadar | Network / Ruch | Odczyt logów Windows/JSONL/Linux, przyrostowe śledzenie rosnącego logu z rotacją, heurystyka prób portów i ograniczony Windows TCP SYN metadata capture bez payloadu; brak pełnego Deep Capture | Fixture/GUI PASS; realnego przechwytywania nie testowano | Nie | Legacy |
| Network Snapshot | Network / Historia | Zapis/porównanie migawek, historia obserwacji; porównanie ze starym formatem hosts, normalizacja MAC i scalenie IP tego samego urządzenia oraz zmian nazw i producenta | Core/GUI fixture PASS; pełny parytet discovery/CLI i realny skan niezweryfikowane | Nie | Legacy |
| Nmap Profiles | Network / Porty | Sześć ograniczonych profili, plan, wykonanie, parser i porównanie XML w Core/GUI | Fixture/GUI PASS; Nmap niedostępny lokalnie | Nie | Legacy |
| Network Sentinel (skrypt Dashboardu) | Network / Sentinel | Odczyt bridge/statusu/alertów/historii/list; skan ICMP; własne reguły Firewall IN/OUT; ręczny Deep Capture metadanych TShark/Npcap. Opcjonalna automatyczna blokada po dwóch alertach HIGH, pełnej liście zaufanych i zgodzie na sesję; limit 5 IP. Pełny parytet wykrywania pozostaje | Fixture polityki/parsera/Firewalla/GUI PASS; prawdziwego TShark i blokady w VM nie sprawdzono | Nie | Legacy |
| ADB Diagnostic | Android / ADB | Android Center: wykrywanie autoryzowanych urządzeń, odczyt właściwości/systemu/baterii/pakietów/usług/uprawnień oraz opcjonalne statystyki logcat bez treści | Fixture/GUI PASS; ADB lokalnie bez urządzenia | Nie | Legacy |
| Android Inspector | Android / Aplikacje | Android Center: lista aplikacji, wersje, deklaracje/granty, appops, role i Device Admin z oznaczeniem niepewności; częściowy parytet OEM | Fixture/GUI PASS; bez testu na urządzeniu | Nie | Legacy |
| Security Check | Security / Kontrole | Security Center: 21 odczytowych kategorii Windows i dotychczasowe reguły audytu/scoringu z coverage UNKNOWN; opcjonalna analiza offline JSON | Fixture/GUI PASS; rzeczywisty lokalny audyt: 21 kategorii, 4 UNKNOWN; inne konfiguracje Windows niesprawdzone | Nie | Legacy |
| Malware Triage | Security / Triage | Security Center: 21 odczytowych sekcji, próbka CPU/GPU, procesy, persistence, połączenia, heurystyki i korelacje, rozszerzenia Chromium/Firefox oraz opcjonalny ograniczony skan wskazanego folderu; analiza offline JSON | Fixture/GUI PASS; lokalny odczyt 30 s: 21 sekcji, 1 UNKNOWN, 14 klatek GPU; pełniejszy parytet systemów do sprawdzenia | Nie | Legacy |
| File Inspector | Security / Pliki | Security Center: odczyt pliku bez wykonania, SHA-256/SHA-512/SHA-1/MD5, entropia, typ magic/rozszerzenie, nagłówek PE, opcjonalne ciągi i Authenticode Windows | Fixture/GUI PASS; bez testu podpisanego pliku Windows i pełnego parytetu | Nie | Legacy |
| Windows Toolkit | System / Diagnostyka | Odczyt historii 50 aktualizacji, usług/polityk/restartu oraz plan i kontrolowane wykonanie SFC, DISM scan/restore, flush DNS, reset Winsock i DHCP renew z dziennikiem, migawką i potwierdzeniem braku rollbacku. Pozostała diagnostyka legacy wymaga audytu | Core/GUI i fixture wykonania PASS; rzeczywistych napraw nie uruchamiano | Nie | Legacy |
| PC Cleanup | System / Czyszczenie | System Center: profile TEMP/cache, analiza Downloads/logów/Kosza, plan i kwarantanna tylko zatwierdzonych plików, odtworzenie bez nadpisania nowszego pliku | Fixture clean/restore/kolizja PASS; nie czyszczono danych użytkownika | Nie | Legacy |
| System Snapshot | System / Migawki | System Center: odczyt 12 kategorii Windows, zapis nowego JSON i porównanie offline z identyfikacją zmian | Fixture/GUI PASS; lokalny odczyt 12/12 sekcji bez UNKNOWN | Nie | Legacy |
| Repair Report | Wspólny ReportService | Walidacja i eksport HTML/JSON/TXT/PDF; formularz w System i Security Center. Ostatni udany wynik tych Centrów zasila krótką diagnozę i czynności bez ścieżek/surowych dowodów; klient i test końcowy pozostają puste. Pozostałe Centra jeszcze bez integracji | Core/PDF, prefill/GUI i kontrola wizualna długiego PDF PASS | Nie | Legacy |
| Backup | Storage & Recovery / Backup | Backend kopii folderu, planu, SHA-256/manifestu, weryfikacji, odtwarzania do nowego katalogu, eksportów serwisowych, ACL i VSS w `prestige_core.backup`; GUI udostępnia wiele źródeł, cztery wykrywane foldery standardowe, zakładki i kopię samego eksportu. Pełny parytet UX niepotwierdzony | 29 zaadaptowanych testów legacy, fixture GUI i odczyt 4/4 folderów lokalnego Windows PASS; rzeczywistego VSS/ACL Windows nie uruchamiano | Nie | Legacy + Center |
| USB Toolkit | Storage & Recovery / USB | Inwentaryzacja dysków oraz `prestige_core.usb`: odczytowy plan z walidacją wersji i celu, przygotowanie zestawu, manifest, weryfikacja, aktualizacja wersji z kopią i cofnięciem; GUI pokazuje plan wielu narzędzi. Pełny parytet UX i nośników niepotwierdzony | 16 zaadaptowanych testów legacy PASS, plan bez zapisu i smoke GUI PASS; fizycznego USB nie testowano | Nie | Legacy + Center |
| Folder Watch | Monitor / Zdarzenia | Polling z hashowaniem, JSONL i SQLite/importem obu starych schematów (polling oraz native bez stanu); Windows native Security/Attributes z korelacją zmian treści/ACL/ADS przez skan przed/po. Audyt funkcji w `FUNCTION-PARITY-AUDIT.md` | Core/GUI, import native bez fikcyjnego baseline i syntetyczna korelacja PASS; duże drzewa, overflow oraz zmiana ACL w ograniczonym koncie niezweryfikowane | Nie | Legacy + Center |
| Integrity Monitor | Monitor / Integralność | SHA-256, baseline, porównanie i kontrolowana aktualizacja z kopią .bak; ręczny skan ACL/ADS i podpis Ed25519 z weryfikacją. Stary baseline można importować do nowego pliku, bez nadpisania oryginału; niepełny pozostaje UNKNOWN | Import fixture, Core/GUI PASS; realny ACL/ADS na ograniczonym koncie niezweryfikowany | Nie | Legacy + Center |
| Hash Checker | Monitor / Hash | Hash pliku, manifest folderu, zapis i weryfikacja, porównanie dwóch folderów i dwóch manifestów w GUI; czytanie starego formatu manifestu; odłączony podpis Ed25519 z weryfikacją względem wskazanego klucza; SHA1/MD5 tylko kompatybilność. Stare repo zarchiwizowane, publiczne | Core/GUI fixture PASS; zgodność starych/nowych manifestów i podpisów w obie strony PASS; końcowy test EXE niezweryfikowany | Nie | Legacy + Center |
| Termux Setup | Termux Center / Setup | Wspólny CLI i GUI z pięcioma profilami, planem, instalacją przez pkg tylko w Termux, konfiguracją PATH/Git/klienta SSH oraz kopią i warunkowym cofnięciem | Fixture konfiguracji/cofnięcia i odmowy przy zmienionym pliku PASS; fizyczny Termux/pkg niesprawdzony | Nie | Legacy |
| Termux Toolkit | Termux Center / Toolkit | Wspólny CLI i GUI z ośmioma kategoriami i operacjami, SHA-256 pliku, archiwum tar z wykluczeniem znanych sekretów i manifestem SHA-256 | Fixture poleceń, archiwum i verify PASS; polecenia Android/Termux:API na urządzeniu niesprawdzone | Nie | Legacy |
| AI Diagnostic Assistant | Wspólna analiza | Core ma normalizację raportów Centrów, lokalne reguły, punktację i opcjonalny provider OpenAI z podglądem metryk bez alertów opisowych; wspólny ekran w System i Security Center z potwierdzeniem wysyłki oraz eksportem JSON/PDF | 3 testy Core/GUI PASS; zewnętrzny provider i koszty API niezweryfikowane na rzeczywistym koncie | Nie | Legacy |
| Tech CLI | Wspólny CLI | Instalowalna komenda `prestige` uruchamia 10 nowych Centrów, przekazuje argumenty i kody wyjścia; `legacy` zachowuje katalog 26 samodzielnych narzędzi; `ai` daje lokalną analizę, podgląd i jawne `--send` | Testy dry-run/forwarding i zainstalowany wheel: smoke System/AI/Report PASS; brak pełnego testu EXE i wszystkich 26 legacy backendów | Nie | Legacy |
| Tech Dashboard | Launcher | Dodano pozycje 10 nowych Centrów obok programów legacy; wygląd bez zmian | Testy integracji Dashboardu PASS; EXE Centrów niezweryfikowane | Nie dotyczy | Legacy + Centra |

Nowe zakresy bez starego odpowiednika: Registry Manager ma 29 ręcznych
odczytów oraz 471 odrębnych odczytów z lokalnych ADMX na tym komputerze;
wszystkie 500 wywołań wykonano bez zapisu rejestru (66 wartości dostępnych,
434 nieustawione zasady lub nieistniejące klucze). Dziewięć zmian HKCU Explorer
ma kopię i rollback sprawdzone na fixture; zapis Windows/VM niezweryfikowany.
Historyczny opis wcześniejszego etapu: 25 zweryfikowanych
odczytów i jedną operację zapisu sprawdzoną tylko na fixture; szczegóły są
w `REGISTRY-OPERATIONS.md`. Storage & Recovery ma inwentaryzację dysków,
testowy silnik RAW dla plików i backend obrazu PhysicalDrive sprawdzony tylko
na fixture. Registry Manager i Storage & Recovery są dostępne jako pozycje
źródłowe w Dashboardzie, lecz ich nowe EXE nie zostały zweryfikowane.
