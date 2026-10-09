# PRESTIGE TECH — kod i funkcje Centrów

Stan dokumentu: **2026-10-08**. Źródło: bieżący kod repozytorium `prestige-tech`, [status projektu](PROJECT-STATUS.md), [historyczna macierz migracji](development/CENTER-MIGRATION-MATRIX.md) i [plik przekazania](development/CONTINUE-HANDOFF.txt). Dokument opisuje **10 Centrów widocznych w Dashboardzie**, a nie stare samodzielne repozytoria. „W kodzie” oznacza zaimplementowaną ścieżkę; nie oznacza jeszcze potwierdzenia na każdym urządzeniu ani gotowego EXE.

## Mapa kodu

Każdy launcher można uruchomić z katalogu głównego repozytorium po zainstalowaniu zależności GUI. Kod okna jest w pakiecie `prestige_*`, a logika funkcji zwykle w `prestige_core`. Dashboard ma osobne repozytorium `w4sy1/prestige-tech-dashboard`; jego katalog GUI zawiera te 10 Centrów.

| Centrum | Launcher | Okno GUI | Główna logika |
|---|---|---|---|
| Network Center | `network_center.py` | `prestige_network_center/gui.py` | `prestige_core/network*.py`, `dns_*.py`, `internet_*.py`, `nmap_profiles.py`, `traffic_*.py`, `sentinel_*.py`, `device_history.py` |
| Monitor Center | `monitor.py` | `prestige_monitor/gui.py` | `file_snapshot.py`, `watch_state*.py`, `native_*.py`, `event_history.py`, `hash*.py`, `baseline_*.py` |
| Registry Manager | `registry_manager.py` | `prestige_registry/gui.py` | `registry_read.py`, `registry_admx.py`, `registry_audit.py`, `registry_change.py`, `registry_transactions.py`, `registry_policy_changes.py` |
| Storage & Recovery | `storage_center.py` | `prestige_storage/gui.py` | `storage_inventory.py`, `physical_imaging.py`, `backup/`, `usb/` |
| Android Center | `android_center.py` | `prestige_android/gui.py` | `android_adb.py` |
| Security Center | `security_center.py` | `prestige_security/gui.py` | `security_*.py`, `malware_*.py`, `file_inspector*.py`, `file_extended.py` |
| System Center | `system_center.py` | `prestige_system/gui.py` | `system_snapshot.py`, `windows_toolkit.py`, `windows_repairs.py`, `pc_cleanup.py`, `cleanup_runtime.py` |
| Termux Center | `termux_center_gui.py` | `prestige_termux/gui.py` | `termux_setup.py`, `termux_toolkit.py`, `termux_configuration.py`, `termux_runtime.py` |
| AI Center | `ai_center.py` | `prestige_ai/gui.py` | `ai_service.py`, `ai_rules.py`, `ai_normalization.py`, `ai_remote.py`, `ai_providers.py` |
| Report Center | `report_center.py` | `prestige_report/gui.py` | `report_service.py`, `report_prefill.py`, `report_evidence.py`, `report_live.py`, `pdf_export.py` |

## 1. Network Center

**Moduły GUI:** Urządzenia, Skan lokalny, Internet, DNS Center, Porty (Nmap), Historia LAN, Optymalizacja, Ruch (NetRadar), Adaptery i DNS, Sentinel, Historia urządzeń, Zaufane urządzenia.

- Odczyt adapterów i lokalnej tablicy sąsiadów; wpis cache nie dowodzi obecności online. Ograniczony skan własnej podsieci ICMP z opcjonalnym Nmap i reverse DNS; lokalna baza OUI.
- Historia urządzeń w opt-in SQLite, kategorie urządzeń, import starej bazy i listy JSON; pełna obserwacja wymaga potwierdzenia i oznacza brakujące urządzenia jako „niezaobserwowane”, nie „offline”.
- Migawki sieci z bieżącego odczytu, skanu lub listy JSON; zapis wyłącznie do nowego pliku i porównanie zmian.
- Diagnostyka Internetu i kontekstu połączenia/Wi-Fi. Benchmark DNS UDP/TCP, profile resolverów, odczyt wpisów DoH Windows, test systemowego resolvera i opcjonalna historia wyników.
- Sześć profili Nmap; plan, uruchomienie, odczyt i porównanie wyników XML. Odczyt ustawień sieci oraz zmiany DNS IPv4 i MTU z planem, kopią i warunkowym cofnięciem.
- Analiza logów ruchu, śledzenie rosnącego logu i ograniczony odczyt metadanych TCP SYN. Sentinel odczytuje status, alerty, historię i listy znanych/zaufanych urządzeń; ma ręczny Deep Capture metadanych, własne reguły zapory oraz ograniczoną opcjonalną automatyczną blokadę.

**Granice:** brak pełnej konfiguracji DNS IPv6/DoH i części funkcji dawnego Sentinel (zarządzanie listami, harmonogram, autostart, raport HTML). Rzeczywiste Nmap/TShark, zmiany zapory oraz zapis/cofnięcie DNS/MTU wymagają osobnego sprawdzenia.

## 2. Monitor Center

**Moduły GUI:** Migawka, Hash Checker, Zdarzenia.

- Skanowanie folderu i baseline integralności SHA-256; porównanie zmian, kontrolowana aktualizacja baseline z kopią, odczyt ACL/ADS oraz podpis i weryfikacja Ed25519.
- Obserwacja plików przez polling i natywne zdarzenia Windows; korelacja zdarzeń z porównaniem treści, ACL i ADS. Dziennik JSONL, historia SQLite i import wcześniejszych schematów bazy.
- Hash pliku, manifest folderu, weryfikacja manifestu, porównanie folderów i manifestów; podpis manifestu i sprawdzenie podpisu.

**Granice:** duże drzewa, przepełnienie kolejki zdarzeń i ACL na koncie z ograniczonymi uprawnieniami nie mają końcowej weryfikacji.

## 3. Registry Manager

**Moduły GUI:** katalog odczytów, audyt, zmiany HKCU z planem/kopią/cofnięciem.

- Wyszukiwanie po ID/nazwie/kategorii, odczyt wybranej pozycji i odczytowy audyt całego katalogu.
- **29 ręcznych odczytów** i dodatkowe odczyty z lokalnych szablonów ADMX. Na wcześniej sprawdzonym komputerze katalog osiągnął **500 odrębnych odczytów**, z których większość dotyczyła nieustawionych zasad albo nieistniejących kluczy.
- Dwadzieścia zmian HKCU, w tym ustawienia Eksploratora, wyglądu oraz cztery polityki użytkownika, z planem, kopią i cofnięciem; przepływ zmian był sprawdzany na atrapach. Polityki 012–015 są blokowane na niewspieranej edycji Windows, chyba że użytkownik włączy sesyjny tryb eksperymentalny. GUI pokazuje opisy prostym językiem oraz FREE/PRO; wydanie PRO wymaga jeszcze klucza wydawcy i warunków licencyjnych.

**Granice:** 500 odczytów **nie oznacza 500 zmian rejestru**. Liczba pozycji ADMX zależy od instalacji Windows; zapis i rollback na prawdziwym systemie wymagają osobnego testu.

## 4. Storage & Recovery

**Moduły GUI:** dyski/obraz, Backup, PrestigeUSB.

- Inwentaryzacja fizycznych dysków, modelu, rozmiaru, magistrali i woluminów. Kod akwizycji obrazu dysku z odczytu źródła, postępem/przerwaniem i weryfikacją.
- Kopie jednego lub wielu folderów, standardowych katalogów użytkownika oraz wybranych zakładek; manifest i SHA-256, sprawdzenie kopii, odtwarzanie do nowego folderu bez nadpisywania. Opcje ACL, VSS i eksportów serwisowych.
- PrestigeUSB: plan, utworzenie zestawu, manifest/weryfikacja, aktualizacja narzędzia z kopią i cofnięcie aktualizacji — bez formatowania nośnika.

**Granice:** programowy tryb odczytu nie gwarantuje fizycznej blokady zapisu. Akwizycja prawdziwego dysku, VSS/ACL i USB nie mają końcowego testu na docelowym sprzęcie.

## 5. Android Center

**Moduły GUI:** Urządzenia, ADB Diagnostic, Android Inspector.

- Wykrywanie urządzeń ADB i kontrola autoryzacji. Odczyt właściwości Androida, systemu, baterii, pakietów, usług i uprawnień; opcjonalne statystyki logcat bez treści wpisów.
- Lista aplikacji, wersje, deklarowane/przyznane uprawnienia, AppOps, role i Device Admin z oznaczeniem niepewności danych zależnych od producenta.

**Granice:** brak końcowego testu na fizycznym telefonie i pełnego potwierdzenia zachowania na różnych nakładkach OEM.

## 6. Security Center

**Moduły GUI:** File Inspector, Security Check, Malware Triage; wejścia do AI i raportu.

- Odczyt pliku bez jego wykonania: SHA-256/SHA-512/SHA-1/MD5, entropia, typ magic/rozszerzenie, nagłówek PE, opcjonalne ciągi i Authenticode Windows; eksport analizy i PDF.
- Odczytowy audyt konfiguracji Windows w 21 kategoriach, reguły oceny z oznaczeniem `UNKNOWN` przy brakach danych oraz analiza zapisanego JSON.
- Malware Triage: procesy, trwałość uruchamiania, połączenia, próbki CPU/GPU, rozszerzenia przeglądarek, korelacje i opcjonalny skan wskazanego folderu; analiza offline JSON.

**Granice:** wyniki heurystyk nie są werdyktem o obecności malware. Podpisany plik Windows i różne konfiguracje systemowe wymagają dodatkowej weryfikacji.

## 7. System Center

**Moduły GUI:** System Snapshot, Windows Toolkit, kontrolowane naprawy, PC Cleanup; wejścia do AI i raportu.

- Zapis migawki systemu i porównanie dwóch migawek. Odczyt 14 sekcji diagnostyki Windows, m.in. aktualizacji, usług, restartu, dysków/SMART/partycji, firmware, aktywacji, Run/RunOnce i zdarzeń.
- Plan i kontrolowane wykonanie SFC, DISM scan/restore, flush DNS, reset Winsock oraz odnowienia DHCP.
- PC Cleanup: plan czyszczenia TEMP/cache, analiza Downloads/logów/Kosza, przenoszenie tylko zatwierdzonych plików do kwarantanny i przywracanie bez nadpisywania nowszego pliku.

**Granice:** właściciel/podpis każdego procesu i pełne pokrycie pól dawnego Windows Toolkit pozostają otwarte; napraw nie wykonywano na hoście w ramach testów kodu.

## 8. Termux Center

**Moduły GUI:** Setup i Toolkit, dostępne też przez `termux_center.py`.

- Setup: pięć profili pakietów, plan instalacji `pkg`, konfiguracja PATH/Git/klienta SSH, kopia i warunkowe cofnięcie zmian.
- Toolkit: osiem kategorii operacji, diagnostyka Termux/Android, SHA-256 pliku, archiwum `tar` z wykluczeniem znanych sekretów i manifestem SHA-256 do weryfikacji.

**Granice:** wykonanie `pkg` i Termux:API na fizycznym urządzeniu nie jest potwierdzone.

## 9. AI Center

**Moduły GUI:** lokalna analiza, podgląd danych, opcjonalne zewnętrzne AI, eksport.

- Normalizacja raportów Centrów, lokalne reguły/punktacja, podgląd dokładnego zestawu danych przed wysyłką, opcjonalny provider OpenAI po osobnym potwierdzeniu, zapis JSON i eksport PDF.
- System i Security Center mają własne wejścia do wspólnej usługi AI.

**Granice:** połączenie z zewnętrznym API i rozliczenie kosztów nie były sprawdzane na rzeczywistym koncie.

## 10. Report Center

**Moduły GUI:** formularz Repair Report i eksport.

- Dane zlecenia, diagnoza, wykonane czynności, wynik końcowy i inne pola formularza; walidacja oraz zapis HTML, JSON, TXT i PDF.
- Ostatni udany wynik System lub Security Center może wstawić krótkie podsumowanie do formularza, bez automatycznego uzupełniania danych klienta i testu końcowego.
- Rozpoznane zapisane JSON z dziewięciu Centrów można dołączyć po podglądzie; formularz dopisuje neutralny opis czynności i sprawdza SHA-256 źródła przed zapisem. Diagnozę oraz test końcowy wypełnia technik.
- Network, Monitor, Registry, Storage, Android, Termux i AI Center mogą otworzyć formularz z neutralnym opisem wybranego bieżącego wyniku bez tworzenia pliku pośredniego. System i Security miały wcześniejsze wejścia do Report.

**Granice:** automatyczne przekazywanie bieżących wyników do raportu nie jest ukończone. Nie każde Centrum ma własny przycisk eksportu rozpoznawanego JSON.

## Historia ostatnich zmian i stan wydania

- **2026-10-08:** Drugi widok strony głównej Dashboardu (bez potwierdzenia 1:1); lista kopii DNS, filtry zdarzeń Monitora, migawki Android offline, porównanie zakresu audytów Security, metadane dzienników System, odczyt środowiska Termux, tryb AI tylko lokalnie oraz manifest SHA-256 odniesień do plików Report. Pozostałe pozycje tabeli wymagają wdrożenia lub pełnego audytu.
- **2026-10-07:** Network Center ma plan, zapis i warunkowe cofanie DNS IPv6 z oddzielną kopią i wyborem rodziny w GUI. Logika i smoke źródłowego GUI przeszły testy; rzeczywisty zapis wymaga testu administratora na Windows.
- **2026-09-30:** Network Center otrzymał odczyt wpisów DoH Windows, test systemowego DNS z limitem czasu, opcjonalną historię DNS, import obserwacji LAN JSON i migawkę z listy JSON bez nadpisywania. Ostatnio zapisana suita repozytorium: **237 testów, 236 zaliczonych, 1 pominięty**.
- **2026-09-30:** 19 starych osobnych repozytoriów zapisano lokalnie i usunięto z GitHuba; katalog GUI Dashboardu ograniczono do 10 Centrów. Archiwum: `C:\Users\01dwa\Documents\PrestigeTech-Legacy-Archive-2026-09-30`.
- Kod Centrów i dokumentacja są w `w4sy1/prestige-tech`, Dashboard w `w4sy1/prestige-tech-dashboard`. **Nowych EXE Centrów nadal nie uznano za zweryfikowane.**
- Aktualną licencję własnego kodu określa [LICENSE](LICENSE): **Prestige Tech Free Use License**.

## Plan rozbudowy kodu `.py` — dwa style Dashboardu

Aktualizacja 2026-10-08: do kodu dodano opcjonalny test HEAD HTTP/HTTPS w
Internet Diagnostic, odczyty CPU/GPU/BIOS/dysków/SMART w System Snapshot,
odczytową analizę zajętości i dużych plików w PC Cleanup, listę obecnych
urządzeń USB PnP z VID/PID oraz lokalne połączenie 2–10 raportów w AI Center.
Poniższa tabela ma charakter historycznego planu; stan bieżący opisuje
`PROJECT-STATUS.md`. Distant i pełny iDiagnostics nie są ukończone.

Ustalenie z 2026-10-07: obecny niebieski Dashboard zostaje. Drugi styl ma prostszą hierarchię **stan komputera → Centra → konkretne działania**, z kartami, ikonami i krótkim opisem. Oba style mają korzystać z tego samego katalogu 10 Centrów, tych samych danych, operacji i ustawień; wybór stylu jest prezentacją, nie osobną kopią logiki. Wskazany czat zawiera opis, ale nie udostępnia grafik referencyjnych, więc dokładny wygląd drugiego stylu nie jest jeszcze specyfikowany piksel po pikselu.

Technicznie warstwę stylów można przełączać przez arkusz stylów aplikacji Qt, a wybór użytkownika zapisać przez `QSettings`; oba mechanizmy są opisane w [dokumentacji Qt Style Sheets](https://doc.qt.io/qtforpython-6/overviews/qtwidgets-stylesheet-syntax.html) i [QSettings](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QSettings.html). To propozycja implementacji, jeszcze nie gotowy przełącznik.

Wszystkie pozycje „Do dopisania” poniżej to **propozycje, nie gotowe funkcje**. Priorytet: kod źródłowy Python, testy jednostkowe i testy na danych symulowanych. Testy na urządzeniu, sieci produkcyjnej i fizycznym dysku oraz pakowanie EXE są późniejszym etapem.

| Moduł | Funkcje już w kodzie — skrót | Do dopisania w `.py` |
|---|---|---|
| **Dashboard** | Katalog 10 Centrów, strona główna, moduły, aktualizacje, narzędzia systemowe, raporty, ustawienia i poradnik; obecny niebieski styl | Drugi styl z trzema poziomami informacji; przełącznik stylu w ustawieniach z zapamiętaniem wyboru; wspólne modele kart i statusów bez dublowania akcji; możliwość powrotu do obecnego stylu |
| **Network Center** | LAN, Internet/Wi-Fi, DNS benchmark i historia, sześć profili Nmap, migawki, DNS IPv4/IPv6 i MTU z kopią, analiza ruchu, Sentinel: zmiana zaufania z kopią/cofnięciem, sesyjny harmonogram ICMP i raport LAN HTML | Pełna obsługa list znanych urządzeń Sentinel; przegląd i audyt harmonogramu po wielu sesjach; parytet wszystkich funkcji starego Sentinel |
| **Monitor Center** | Baseline i hash plików, ACL/ADS, polling i natywne zdarzenia, dziennik, SQLite, manifesty i podpisy Ed25519; filtry osi czasu, profile skanu/pollingu z wykluczeniami oraz porównanie okresów | Pełna sygnalizacja utraconych zdarzeń/niepełnego skanu we wszystkich trybach; spójne wykluczenia w obserwatorze natywnym lub jawne utrzymanie tego ograniczenia |
| **Registry Manager** | Odczyty ręczne i ADMX, audyt, 20 zmian HKCU z planem/kopią/cofnięciem, podgląd rollbacku i eksport różnicy JSON dla dotychczasowych zmian | Cel 200/200/200 zmian; indywidualna weryfikacja działania i wersji Windows; pełny wspólny eksport różnicy dla nowych polityk |
| **Storage & Recovery** | Dyski i obrazowanie, kopie/manifest/SHA-256, odtwarzanie, ACL/VSS, zestawy PrestigeUSB i rollback | Dziennik akwizycji z checkpointami i kontrolą wznowienia; raport źródło–cel–hash bez twierdzenia o fizycznej blokadzie zapisu; kontrola, że cel obrazu nie wskazuje źródła; widok wersji kopii i zajętości miejsca przed operacją |
| **Android Center** | ADB Diagnostic, lista aplikacji, uprawnienia/AppOps, role, Device Admin | Porównanie dwóch migawek urządzenia lub aplikacji; profil wielu urządzeń z jednoznacznym wyborem serialu; raport zmian uprawnień; analiza wcześniej zapisanego wyniku ADB bez telefonu |
| **Security Center** | Security Check, Malware Triage, File Inspector, eksport i AI/raport, porównanie audytów i zapis audytu JSON | Wspólna oś ustaleń z pochodzeniem dowodów; pakiet materiału diagnostycznego z redakcją danych osobowych; priorytety działań z oznaczeniem `UNKNOWN` zamiast automatycznego werdyktu |
| **System Center** | Migawki, diagnostyka Windows, SFC/DISM i naprawy sieci z planem, PC Cleanup z kwarantanną | Właściciel/podpis procesu w diagnostyce; porównanie stanu przed i po naprawie; plan zależności i restartu; wspólny dziennik wykonanych czynności dla Report Center |
| **Termux Center** | Pięć profili Setup, osiem kategorii Toolkit, `pkg`, konfiguracja środowiska, hash i archiwum `tar`, odczyt stanu z eksportem JSON oraz porównanie pakietów profilu z `dpkg-query` | Eksport pełnej konfiguracji z ukryciem sekretów; raport błędów z jasnymi krokami cofnięcia |
| **AI Center** | Lokalna analiza regułowa, podgląd danych, opcjonalne zewnętrzne AI, JSON/PDF | Śledzenie źródła każdej tezy do wyniku Centrum; automatyczna redakcja danych w podglądzie; limit rozmiaru i szacowanie zakresu wysyłki; tryb „tylko lokalnie” zapamiętywany w ustawieniach |
| **Report Center** | Formularz i eksport HTML/JSON/TXT/PDF, częściowe wstawianie wyników System/Security, import rozpoznanych JSON z dziewięciu Centrów i manifest SHA-256 odniesień | Automatyczne przekazywanie bieżących wyników; eksport z GUI tam, gdzie go brakuje; szablony raportu zależne od typu sprawy |

Wdrożenie tych propozycji wymaga osobnego sprawdzenia pozycja po pozycji. Nie należy zwiększać liczników funkcji ani ogłaszać pełnego zakresu na podstawie samej tabeli.
