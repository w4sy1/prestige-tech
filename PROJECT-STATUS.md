# Prestige Tech — stan realizacji

Aktualna licencja własnego kodu: **Prestige Tech Free Use License** (`LICENSE`).
Wpisy historyczne poniżej opisujące MIT odnoszą się do wcześniejszych stanów
projektu i nie zastępują bieżącego pliku licencji.

Bieżący plik przekazania pracy i lista końcowych testów: `development/CONTINUE-HANDOFF.txt`.

## Publikacja kodu źródłowego — 2026-09-28

Dziesięć Centrów i dokumentacja wersji testowej są na domyślnej gałęzi
`w4sy1/prestige-tech` ([PR #1](https://github.com/w4sy1/prestige-tech/pull/1)).
Połączenie źródłowych Centrów z Dashboardem jest na domyślnej gałęzi
`w4sy1/prestige-tech-dashboard`
([PR #1](https://github.com/w4sy1/prestige-tech-dashboard/pull/1)); jego GitHub
Actions przeszedł na Pythonie 3.11 i 3.14 także po scaleniu. Historycznie
opublikowano 26 repozytoriów z prefiksem `prestige-`; po usunięciu pięciu
zdublowanych pozostało 21, w tym główne repo i Dashboard. Opisy wskazują Prestige Tech Free Use
License. Nie opublikowano nowych EXE ani release Centrów.
Ręczne testy urządzeń, VM, skalowania GUI i działania instalacyjnych EXE
pozostają do wykonania przez użytkownika na końcu.

## Aktualny etap — 2026-09-29

Audyt File Inspector: Security Center ma odpowiedniki analizy pliku, a
wspólne CLI obsługuje teraz `prestige file PLIK [--strings] [--output KATALOG]
[--pdf NOWY_PLIK]`. Raporty JSON/TXT/HTML i PDF korzystają ze wspólnych usług.
Security Center ma przyciski eksportu ostatniej udanej analizy pliku;
po błędzie lub nowej operacji eksport jest wyłączany.
Hash, entropia i próbka ciągów powstają z jednego odczytu pliku. Osobne
repozytorium pozostaje do weryfikacji podpisu Authenticode, końcowego EXE
i pełnej zgodności raportów. Szczegóły w `development/FUNCTION-PARITY-AUDIT.md`.
Porównanie 4 lokalnych plików w obu trybach ciągów: pola analizy identyczne;
nowy kod wybiera `pwsh`, jeśli jest dostępny. Podpisanego pliku nie sprawdzono,
a wrapper nowego raportu nie zawiera starego pola `version`.

## Poprzedni etap — 2026-09-28

Osobne repozytoria `prestige-system-snapshot`, `prestige-security-check`,
`prestige-repair-report` i `prestige-pc-cleanup` usunięto z GitHuba po
sprawdzeniu odpowiedników w Centrach i testów. Ich pełne historie Git mają
zweryfikowane bundle w `C:\Users\01dwa\.codex\backups\prestige-tech-legacy`;
lokalne checkouty zachowano. Stare EXE nadal są w wydaniu zbiorczym.
Dashboard nadal zawiera zarówno te cztery stare EXE, jak i Centra; niczego
z jego katalogu nie usunięto. Testy: cztery stare suity 14/19/11/17 PASS,
`prestige-tech` 213 PASS i 2 skip, Dashboard 16 PASS. Testy nowych EXE
Centrów oraz rzeczywiste operacje czyszczenia pozostają otwarte.

Po audycie funkcji i dwukierunkowym sprawdzeniu manifestów/podpisów stare
repozytorium `w4sy1/prestige-hash-checker` usunięto z GitHuba (API: 404).
Pełna historia Git ma zweryfikowany lokalny bundle w
`C:\Users\01dwa\.codex\backups\prestige-tech-legacy\prestige-hash-checker-2026-09-28.bundle`;
lokalny checkout także pozostał. Stary EXE jest w wydaniu głównego repo.
Dashboard nadal zawiera Hash Checker oraz Monitor i nie pobiera starego
modułu z osobnego repo; jego 16 testów PASS. Dwa zastane pliki nieśledzone
Dashboardu pozostały bez zmian. Nowe EXE Monitora pozostaje niezweryfikowane.

Network Snapshot scala teraz wiele IP tego samego MAC przy porównaniu oraz
normalizuje zapis MAC z myślnikami i dwukropkami. Fixture starego formatu
`hosts` z dwoma nowymi wierszami PASS. Pełna suita: 215 uruchomionych,
213 zaliczonych, 2 pominięte. Discovery i realny skan nadal wymagają audytu.

USB Toolkit w Storage & Recovery ma teraz odczytowy plan przygotowania zestawu,
który sprawdza nazwy, wersje, duplikaty i cel przed potwierdzeniem GUI.
Potwierdzenie pokazuje wersje narzędzi. Plan nie tworzy katalogu; fixture i
GUI PASS. Pełna suita: 214 uruchomionych, 212 zaliczonych, 2 pominięte.
Fizycznego USB ani utraty połączenia nie testowano.

GUI Storage & Recovery ma wybór czterech standardowych folderów użytkownika
przez pola wyboru. Ścieżki są wykrywane na bieżąco; niedostępny katalog
blokuje plan. Testy GUI łączenia z ręcznym wyborem i błędu PASS; lokalny
odczyt Windows wskazał 4/4 istniejące foldery. Rzeczywistej kopii tych
folderów nie wykonano.
Pełna suita: 211 uruchomionych, 209 zaliczonych, 2 pominięte.

GUI Storage & Recovery pozwala utworzyć kopię zawierającą tylko eksport
systemu, sterowników lub zakładek, bez wybierania folderu źródłowego. VSS
nadal wymaga folderu. Fixture kopii samych zakładek, manifestu i GUI PASS;
eksportu systemu/sterowników na prawdziwym Windows nie testowano.
Pełna suita po zmianie: 209 uruchomionych, 207 zaliczonych, 2 pominięte.

Audyt Folder Watch wykrył drugi wariant starej bazy SQLite: tryb native
zapisuje zdarzenia bez tabeli stanu. Monitor importuje teraz także tę historię
do nowej bazy, pozostawiając baseline pusty do pierwszego skanu. Test importu
i testy GUI Monitora PASS. Szczegóły w `development/FUNCTION-PARITY-AUDIT.md`.
Pełna suita: 206 uruchomionych, 204 zaliczone, 2 pominięte.

Monitor importuje teraz baseline starego Integrity Monitor do nowego pliku,
po walidacji ścieżek, hashy i kompletności ACL/ADS. Oryginał pozostaje bez
zmian; niepełne dane pozostają UNKNOWN. Dwa testy importu i smoke GUI PASS.
Najnowsza suita: 205 uruchomionych, 203 zaliczone, 2 pominięte.
Szczegóły w `development/FUNCTION-PARITY-AUDIT.md`.

Audyt funkcja po funkcji rozpoczęto w `development/FUNCTION-PARITY-AUDIT.md`.
GUI Storage wybiera teraz wiele folderów źródłowych i plików zakładek oraz
wiele narzędzi dla przygotowania/aktualizacji PrestigeUSB, zgodnie z backendami
starych programów. Najnowsza suita: 202 uruchomione, 200 zaliczonych,
2 pominięte; smoke Storage i Monitor PASS. Pełne potwierdzenie
parytetu nadal wymaga testów rzeczywistego VSS/ACL/USB i pozostałych modułów.

Storage & Recovery: przeniesiono backend Backup do `prestige_core.backup` bez
zależności od starego repozytorium: plan, kopia folderu, manifest SHA-256,
weryfikacja, odtwarzanie do nowego katalogu, eksporty serwisowe, ACL i VSS.
GUI ma wybór folderów oraz tworzenie/sprawdzenie/odtworzenie kopii z opcją ACL,
VSS, eksportem systemu/sterowników/zakładek i odzyskaniem migawek z dziennika.
W jednym przebiegu GUI może wybrać wiele folderów i plików zakładek. 29 testów
starego Backup zaadaptowanych do nowej ścieżki przeszło, podobnie dwa nowe
testy migracji i smoke GUI. Cała suita nowego repo po migracji Backup i USB:
W poprzednim etapie 198 testów uruchomiono: 196 przeszło, 2 pominięte.
Rzeczywistego VSS/ACL Windows, dużej kopii ani pełnego parytetu GUI nie
zweryfikowano. USB Toolkit ma teraz w Storage & Recovery backend i GUI
przygotowania, weryfikacji, aktualizacji i rollbacku wersji narzędzia.
Zaadaptowanych 16 testów starego USB Toolkit i nowy test migracji przeszły;
fizycznego nośnika nie testowano.

Monitor / Hash Checker: dodano w GUI porównanie dwóch folderów i dwóch
manifestów oraz zgodny odczyt starego manifestu `schema_version=1` bez pola
`complete`. Walidacja ścieżek i hashy pozostaje wymagana; test starego formatu
i smoke Monitora przeszły. Pozostała kontrola parytetu funkcja po funkcji.

GUI i Dashboard: dziesięć źródłowych Centrów (Network, Monitor, Registry,
Storage, Android, Security, System, Termux, AI i Repair Report) ma wspólny
ciemny motyw z kartami i widocznym fokusem; Termux, AI i Report dostały
spójny nagłówek. Samodzielne launchery wszystkich Centrów ładują dołączoną
czcionkę, także przy starcie z Dashboardu. Sąsiednie repozytorium
`prestige-tech-dashboard` ma 10 nowych pozycji katalogu oraz bezpieczną,
stałą mapę źródłowych launcherów. Dashboard zachował układ i styl; w trybie
źródłowym przycisk „Uruchom z kodu” otwiera każde Centrum. Wbudowane EXE
tych Centrów nie są jeszcze sprawne ani zweryfikowane, więc to nie jest
potwierdzenie gotowości wersji instalacyjnej. Dziesięć smoke GUI, smoke
Dashboardu i jego 16 testów oraz 194 testy Core przeszły (2 pominięte).
Wizualny podgląd wykonano dla Termux Center przy 850×650; pozostałe
rozdzielczości i zgodność pikselowa z referencjami pozostają do sprawdzenia.

Registry Manager: 29 ręcznych odczytów i 471 unikalnych odczytów zasad
z 33 lokalnych szablonów ADMX Microsoftu daje **500 odrębnych operacji odczytu
na tym komputerze**. Wszystkie wykonały się bez zapisu rejestru: 66 dostępnych
wartości, 434 nieustawionych zasad lub nieistniejących kluczy. Na innym Windows
liczba szablonów może być inna. GUI pozwala wczytać ADMX i filtrować katalog.
Zbiorczy audyt całego katalogu pokazuje tylko liczbę dostępnych i nieustawionych
zasad, z możliwością przerwania; nie zapisuje treści wartości.
Dziewięć wąskich zmian HKCU Explorer ma kopię i warunkowe cofnięcie; osiem
nowych zmian przeszło fixture, ale żadnego zapisu nie sprawdzono w VM.
To nie oznacza 500 operacji zapisu ani pełnego parytetu starego Registry Tool.

Network Center ma teraz DNS Benchmark w karcie DNS (profile, pomiar UDP/TCP,
ranking, przerwanie) oraz przypina lokalny kontekst Wi-Fi do wyniku Internet
Diagnostic. Sentinel otrzymał ręcznie uruchamiany Deep Capture TShark/Npcap:
metadane ARP/TCP/UDP/ICMP, limity pamięci i czasu, heurystyczne alerty;
payload nie jest zapisywany. Monitor koreluje natywne zdarzenia Windows ze
zmianami treści, ACL i ADS przez pełny skan przed/po. Testy syntetyczne i smoke
GUI przechodzą; rzeczywistego Deep Capture, zmian ACL pod ograniczonym kontem
ani dużych drzew nie sprawdzono. Sentinel ma także opcjonalną automatyczną
blokadę własnymi regułami IN/OUT po dwóch oddzielnych alertach HIGH, po
pełnym odczycie zaufanych urządzeń, z limitem pięciu adresów na sesję.
Politykę i Firewall sprawdzono na atrapach, bez zmiany zapory hosta.
Repair Report w System i Security Center wstępnie wypełnia diagnozę i wykonane
czynności z ostatniego udanego wyniku; nie kopiuje ścieżek ani surowych dowodów,
a klient i test końcowy pozostają puste. System Center ma także plany i
kontrolowane wykonanie sześciu napraw Windows Toolkit: SFC, DISM scan/restore,
flush DNS, reset Winsock i odnowienie DHCP. Wymaga administratora, wskazanego
katalogu dziennika, migawki diagnostycznej i potwierdzenia braku rollbacku.
Testy atrap PASS; poleceń nie uruchamiano na hoście. Pełny parytet legacy,
pełny parytet Backup/USB i zasilanie raportów z pozostałych Centrów nadal pozostają.

## Konsolidacja centrów — rozpoczęta 2026-09-26

Plan migracji 26 programów do większych centrów i wykryte duplikaty opisano w
`development/CONSOLIDATION-MAP.md`. Audyt wykazał identyczne pliki wykrywania
LAN w LAN Radar i Network Snapshot oraz wiele kopii `runtime.py` i eksportu PDF.
Wykonane i brakujące odpowiedniki na poziomie każdego starego modułu zapisano
w `development/CENTER-MIGRATION-MATRIX.md`.
Instalowalny Tech CLI `prestige` ma polecenia `center`, `legacy` i `ai`.
Wheel zawiera launchery 10 Centrów; po instalacji smoke System/AI/Report
przeszedł. Stare 26 narzędzi pozostaje dostępnych przez `legacy` z ustawionym
`--tools-root`; pełnych backendów i EXE nie przetestowano.
Wspólne AI analizuje lokalnie raporty nowych Centrów, a przed opcjonalną
wysyłką do OpenAI pokazuje dokładne metryki bez opisowych alertów źródłowych.
Osobne potwierdzenie i ponowna kontrola metryk chronią przed wysłaniem
zmienionego raportu. Ekran jest w System i Security Center, ma eksport JSON/PDF.
Rzeczywistej wysyłki do API nie sprawdzono.
Termux Center łączy Setup i Toolkit we wspólnym CLI i źródłowym GUI: profile
pakietów, plan/konfigurację z kopią i cofnięciem oraz osiem kategorii operacji,
w tym backup tar z manifestem SHA-256. Fixture przeszły; fizycznego Termuxa,
`pkg` i Termux:API nie testowano.
System Center przenosi też odczytowy wycinek Windows Toolkit: historię 50
aktualizacji, usługi i polityki aktualizacji oraz sygnały restartu. Lokalny
odczyt wszystkich czterech sekcji przeszedł; naprawy pozostają w legacy.
Wspólny ReportService przenosi formularz Repair Report oraz lokalny eksport
HTML/JSON/TXT i PDF Unicode do System i Security Center. Długi PDF sprawdzono
na czterech wyrenderowanych stronach; brak jeszcze automatycznego pobierania
wyników z pozostałych Centrów. Bieżąca nowa suita Core/Centrów: 194 testy, 1 pominięty.
Istniejące aplikacje i wydania nie zostały usunięte. Dashboard ma już własny
system komponentów PySide6, ale nadal wskazuje 26 modułów i stare nazwy EXE.

Pierwszy kod wspólnego Core to `prestige_core.FileHashService`: jeden odczyt
pliku może wyliczyć kilka hashy i wykrywa zmianę pliku podczas odczytu.
Jest spakowany jako lokalny pakiet Python `prestige-core`, z osobnymi testami.
Pierwszy wycinek Network Center korzysta z `prestige_core.network` i pokazuje
odczyt lokalnej tablicy sąsiadów bez skanowania oraz adaptery, bramy i DNS IPv4.
Ma PySide6 GUI, pomoc, JSON CLI, zapis lokalnej migawki bez nadpisania,
porównanie dwóch migawek w GUI i Core, obsługę błędu, testy i skrypt budowy EXE.
Karta Sentinel czyta istniejący plik mostu JSON v2 i ostatnie alerty JSONL
Network Sentinel bez uruchamiania skanu przy odczycie statusu; rozróżnia aktualny i przestarzały
raport, a uszkodzony wiersz alertu oznacza `UNKNOWN`. Lokalnie status okazał
się nieaktualny, a 5 ostatnich alertów odczytano poprawnie. Monitoring
Firewall ma nowy moduł planowania i własnych reguł IN/OUT z próbą cofnięcia
częściowej zmiany. Testy fixture i lokalny plan odczytowy przeszły; rzeczywistej
blokady/odblokowania w VM nie sprawdzono. Deep Capture nie jest przeniesiony.
Network Center odczytuje teraz również istniejący log historii urządzeń
Sentinel JSONL; błędny wiersz jest sygnalizowany jako `UNKNOWN`. Ma też
ograniczony aktywny skan ICMP lokalnej podsieci do /24 z wyborem adaptera
i przerwaniem. Testy fixture oraz odczyt lokalnych scope przeszły; realnego
skanu LAN jeszcze nie wykonano. Stare automatyczne reguły ochrony pozostają w legacy.
Karta Internet dodaje pomiary ICMP/DNS z opcjonalną trasą i MTU; karta Porty
ma sześć ograniczonych profili Nmap oraz odczyt i porównanie wyników XML.
Testy fixture i smoke GUI przeszły. Nmap nie jest dostępny lokalnie, więc
realnego skanu Nmap nie zweryfikowano. Nie wykonano też pomiaru zewnętrznego
łącza. Lokalny kontekst DHCP/interfejsów/tras/DNS/Wi-Fi jest dostępny
w osobnym odczycie Core/GUI; pełna korelacja z pomiarem pozostaje.
Dodano opcjonalną lokalną bazę historii LAN SQLite. Rejestruje nowe urządzenia
i zmiany IP/MAC, a brak wpisu w cache nie jest zapisywany jako stan offline.
Test utrwalania i ponownego otwarcia bazy przeszedł. Dodano tagowanie,
opcjonalne reverse DNS/OUI i import starej bazy do nowego pliku; testy fixture
przeszły, ale prywatnej bazy użytkownika nie importowano.
Karta Optymalizacja odczytuje sześć sekcji ustawień adaptera (DNS, MTU, TCP,
zasilanie, powiązania i liczbę wpisów cache DNS); lokalny odczyt Windows
przeszedł. Dodano zmianę DNS IPv4 i MTU 576–1500 z kopią, weryfikacją i
warunkowym cofnięciem; testy fixture i lokalne plany przeszły, ale zapisy na
Windows wymagają VM. Jumbo MTU nie jest objęty nowym przepływem. Karta Ruch analizuje logi
Windows/JSONL/Linux heurystyką NetRadar, śledzi przyrostowo rosnący log
z rotacją oraz ma ograniczony odczyt metadanych Windows TCP SYN bez payloadu;
fixture i GUI przeszły, ale rzeczywistego przechwytywania jako administrator
nie sprawdzono. Pełne Deep Capture pozostaje w starym module.
Na tym komputerze wykonano odczytowy skan własnej podsieci Wi-Fi /24:
253 sondy ICMP, 1 odpowiedź i 0 błędów sond. Brak odpowiedzi pozostałych
adresów nie dowodzi, że urządzenia są offline. Diagnostyka Internetu na
1.1.1.1 otrzymała 2/2 odpowiedzi ICMP i poprawną odpowiedź DNS; pojedyncza
próba nie potwierdza stabilności połączenia. Nmap nie jest zainstalowany.
Porównanie migawek Network Snapshot rozpoznaje teraz również stary format
`hosts` i zmiany nazwy hosta lub producenta; test mieszanego formatu przeszedł.
Android Center ma źródłowe GUI do wyboru autoryzowanego urządzenia ADB,
diagnostyki systemu i inspekcji aplikacji. Odczytuje m.in. baterię, pakiety,
uprawnienia, role i appops; opcjonalny logcat zapisuje tylko statystyki błędów,
bez treści wiadomości. Fixture i smoke GUI przeszły. Lokalne ADB działa,
ale nie było podłączonego urządzenia, więc wyników telefonu/OEM nie zweryfikowano.
Security Center ma pierwszy odczytowy odpowiednik File Inspector: analiza pliku
bez wykonania, hashe, entropia, typ pliku, nagłówek PE, opcjonalne ciągi i
stan podpisu Authenticode na Windows. Test fixture i smoke GUI przeszły;
podpisanego pliku Windows nie zweryfikowano w nowym Center. Przeniesiono też
21 kategorii odczytowych Security Check z istniejącymi regułami i coverage
UNKNOWN. Rzeczywisty audyt lokalnego Windows ukończył się: 21 kategorii,
4 UNKNOWN; ten wynik nie jest prawdopodobieństwem infekcji. Malware Triage
ma odczytowy odpowiednik w Core/GUI: 21 sekcji, próbka CPU/GPU, korelacje
procesów z autostartem i połączeniami, rozszerzenia przeglądarek oraz
ograniczony skan wybranego folderu. Lokalny odczyt 1 s ukończył 21 sekcji
z 1 UNKNOWN; odczyt 30 s ukończył 21 sekcji z 1 UNKNOWN i 14 klatkami GPU.
Wyniki heurystyk
nie są werdyktem malware. Analiza offline odmawia uznania brakujących sekcji
za pełny wynik.
System Center ma pierwsze dwie funkcje: System Snapshot odczytuje 12 kategorii
Windows, zapisuje nowy plik JSON bez nadpisania i porównuje migawki po
identyfikatorach tam, gdzie są dostępne. Lokalny odczyt ukończył 12/12 sekcji.
PC Cleanup skanuje profile, tworzy plan, przenosi zatwierdzone pliki TEMP/cache
do nowej kwarantanny i przywraca je bez nadpisania później utworzonych plików.
Downloads/logi/Kosz służą wyłącznie do analizy. Testy fixture obejmują
roundtrip, zmianę pliku, niedozwolony katalog i kolizję; nie czyszczono danych
użytkownika. Windows Toolkit pozostaje w legacy.
Pierwszy wycinek Monitora (`prestige_core.file_snapshot`, `prestige_monitor`)
odczytuje hashe SHA-256 plików, porównuje migawki i oznacza wynik `UNKNOWN`
przy niepełnym odczycie. Ma GUI PySide6 z wyborem katalogu, zapisem i odczytem
baseline oraz przerwaniem między plikami. Obserwacja na żywo działa przez
odczyt co 2 sekundy, porównuje zdarzenia i ponownie hashuje tylko pliki ze
zmienionym rozmiarem lub czasem modyfikacji. Co 30 odczytów (około minutę
przy typowym czasie skanu) ponownie hashuje wszystkie pliki; test potwierdza
wykrycie zmiany treści przy identycznym rozmiarze i czasie modyfikacji.
Monitor zgłasza także modyfikację samego czasu pliku, zgodnie z zachowaniem
legacy Folder Watch. Rozpoznaje też jednoznaczną zmianę nazwy po identyfikatorze pliku i
SHA-256, zachowując starą oraz nową ścieżkę w historii. Bez wiarygodnego
identyfikatora pokazuje osobno dodanie i usunięcie, zamiast zgadywać.
Historia zdarzeń ma filtr w GUI oraz ręczny zapis/odczyt JSON bez
nadpisywania pliku; niezapisane zdarzenia blokują zmianę katalogu. Nie ma
jeszcze pełnego parytetu
Folder Watch/Integrity Monitor ani EXE Monitora.
Wczytany baseline można świadomie zaktualizować po kompletnym skanie;
poprzedni plik zostaje zachowany jako nowa kopia `.bak`. Testy obejmują odmowę
aktualizacji bez potwierdzenia w API i odmowę przy niepełnym skanie.
Opcjonalny automatyczny dziennik JSONL jest tworzony wyłącznie w nowym pliku
poza obserwowanym katalogiem; każde zdarzenie jest utrwalane z `fsync`.
Opcjonalna baza SQLite poza obserwowanym katalogiem przechowuje ostatnią
kompletną migawkę i zdarzenia. Monitor potrafi po restarcie porównać stan
bieżący z zapisanym i pokazać zmiany z przerwy. Obcej bazy nie nadpisuje.
Główna obserwacja domyślnie używa polling. Jest też osobny, ograniczony do 10 sekund
odczyt Windows FileSystemWatcher,
który potrafi pokazać zdarzenia chwilowe (np. plik utworzony i usunięty między
skanami). Potwierdzono lokalnie takie zdarzenie; przepełnienie bufora daje
`UNKNOWN`. Dodatkowy przycisk uruchamia ciągły natywny odczyt w jednym procesie
aż do zatrzymania; test na Windows potwierdził utworzenie i usunięcie pliku
oraz zamknięcie procesu. Historia tego trybu wymaga ręcznego zapisu lub JSONL;
SQLite przechowuje stan trybu polling.
Stara baza SQLite Folder Watch może zostać zaimportowana do nowego pliku bez
zmiany oryginału; test obejmuje stan, zdarzenia, odmowę nadpisania i odrzucenie
ścieżki wychodzącej poza źródło. Czas wykonania starej migawki jest oznaczony
jako nieznany. Przy wznowieniu z SQLite Monitor zawsze ponownie hashuje pliki,
aby wykryć także zmianę treści z identycznym rozmiarem i `mtime`.
Ręczny skan Monitora ma opcję ACL/ADS (Windows SDDL i alternatywne
strumienie); niepełny odczyt daje `UNKNOWN`. Lokalny test ACL oraz zmiany
rzeczywistego ADS przeszedł. Dodano generowanie szyfrowanego klucza Ed25519,
podpis i weryfikację baseline względem wskazanego klucza publicznego. Testy
wykazały odmowę nadpisania i wykrycie zmiany treści; nie testowano wszystkich
odmów dostępu.
Obserwacja polling może teraz pracować w trybie ACL/ADS. Wznowienie z SQLite
odrzuca zmianę trybu, aby nie porównać niezgodnych migawek; test Windows
potwierdził wykrycie zmiany rzeczywistego ADS. Karta Hash Checker oblicza hash
pliku oraz tworzy i sprawdza manifest folderu. Niepełny skan nie może stać się
baseline; SHA-1/MD5 służą wyłącznie do zgodności ze starszymi danymi.
Manifest można teraz podpisać odłączonym podpisem Ed25519 i zweryfikować względem
wskazanego klucza publicznego. Test potwierdza wykrycie zmiany treści pliku manifestu;
podpis nie potwierdza tożsamości właściciela klucza.
Registry Manager ma odczytowy GUI i 25 udokumentowanych operacji: lokalizacje
folderów, Run/RunOnce oraz odrębne wartości Explorer, UAC, proxy, RDP i ścieżek
systemowych. Fixture i lokalny odczyt Windows przeszły dla wszystkich 25;
nie wykonywano zapisów rejestru. Dodano REG-WRITE-001 (HKCU HideFileExt=0)
z kopią JSON i warunkowym cofnięciem; test fixture przeszedł, ale rzeczywisty
zapis/rollback na VM jest niezweryfikowany i nie zwiększa licznika 25/500.
Licznik 25/500 i pozostałe 475 operacji są w
`development/REGISTRY-OPERATIONS.md`.
Storage & Recovery ma pierwszy odczytowy widok fizycznych dysków, numeru
PhysicalDrive, rozmiaru, magistrali, liter woluminów i ostrzeżenia o dysku
systemowym. Po wybraniu dysku pokazuje jego `UniqueId`. Odczyt lokalny wykrył
1 dysk systemowy; nie otwierano urządzenia blokowo ani nie zmieniano atrybutu
readonly. Dodano osobny backend obrazu RAW `PhysicalDrive` tylko dla dysku
niesystemowego z atrybutem read-only i celu na innym dysku. GUI umożliwia
wybór obrazu i przerwanie, a backend zapisuje metadane oraz weryfikuje obraz
SHA-256. Test fixture przeszedł; prawdziwego dysku fizycznego nie otwierano.
Atrybut Windows read-only nie jest sprzętową blokadą zapisu.
Get-Disk może pomijać dyski dynamiczne. BitLocker i ochrona sprzętowa nie są
jeszcze weryfikowane.
Testowy silnik RAW (`prestige_core.imaging_fixture`) kopiuje wyłącznie zwykły
plik do nowego `.img`, liczy SHA-256, ponownie odczytuje obraz i zapisuje
metadane `COMPLETE`/`INCOMPLETE`. Test potwierdza niezmienność pliku źródłowego,
odmowę nadpisania istniejącego obrazu i oznaczenie przerwania. Nie przyjmuje
PhysicalDrive i nie jest write blockerem.
Natywny backend legacy Folder Watch w `prestige-folder-watch/native.py`
(Windows FileSystemWatcher przez PowerShell) posłużył jako punkt odniesienia
dla ograniczonego i ciągłego odczytu w nowym GUI. Nadal trzeba sprawdzić
pełny parytet, w tym zachowanie przy błędach i restarcie.
Network Center nie jest jeszcze pełny;
stare moduły nadal zawierają duplikaty, a Dashboard nie został jeszcze
przełączony. Testy źródłowe przechodzą, natomiast EXE z PyInstaller
nie przechodzi kontroli startu: wersje diagnostyczne z PySide6 6.11.2
zwracały błąd ładowania DLL przy imporcie QtWidgets na Pythonie 3.14 i 3.13.
Build diagnostyczny onedir/console z PySide6 6.10.2 na Pythonie 3.13
potwierdził ten sam błąd importu QtWidgets. Import działa poza pakietem;
dokładna brakująca procedura DLL pozostaje nieustalona. Minimalny EXE z samym
importem `PySide6.QtWidgets` odtwarza błąd, więc źródłem jest pakowanie Qt w
tym środowisku, a nie logika Network Center. Z tego powodu nie
udostępniono nowego modułu w Dashboardzie ani wydania. Do dalszych etapów
pozostają poprawa pakowania, dalsze funkcje Network Center,
Monitor, kolejne centra, migracja funkcji, testy
sprzętowe, aktualizacja Dashboardu i pełny build. Prestige Distant,
iDiagnostics oraz Registry Tool wymagają ustalenia lokalizacji kodu.

Stan roboczy 2026-09-28: gałąź `codex/consolidation-audit`; 147 testów Core,
Network Center, Monitora, Registry Managera, Storage, Android, Security i System Center przechodzi (1 test dowiązania pominięty z powodu uprawnień), siedem GUI przechodzi smoke z kodu
źródłowego. Network Center odczytał lokalnie 1 wpis cache i 3 adaptery.
Dashboard nie został zmieniony. Manualne testy EXE przez użytkownika są
odłożone do końcowego etapu; automatyczny test startu nadal jest negatywny.
Ostatni build Network Center nie może być traktowany jako działający;
minimalny konsolowy EXE potwierdził błąd importu QtWidgets. Następne
prace: integracja ACL/ADS z obserwacją Monitora i test odmowy dostępu, dalsze funkcje Network
Center bez duplikowania istniejącego DNS Center, Registry Manager, Storage &
Recovery, testy parytetu, integracja Dashboardu.

## Publikacja GitHub — 2026-09-15

Opublikowano 26 samodzielnych repozytoriów i główne `w4sy1/prestige-tech`, wszystkie publiczne na MIT. Każde ma wydanie Pre-release; główne wydanie 0.3.4 zawiera pełną paczkę Windows i źródła. Linki: [PROGRAMS.md](PROGRAMS.md).

Najnowsze testy GitHub Actions wszystkich 26 programów przeszły na Pythonie 3.11 i 3.14. Poprawiono wyłącznie ścieżki w testach PC Cleanup i Termux Setup, aby symulacje błędów działały także przy aliasach katalogu TEMP w Windows. Opublikowane tagi i EXE zachowano; poprawki testów są na domyślnych gałęziach, po tagach wydania. Historyczne wpisy poniżej opisują stan sprzed publikacji.

Gitleaks nie wykrył sekretów w historii 27 repozytoriów. Sumy SHA-256 wszystkich EXE oraz obu zbiorczych archiwów są zgodne z metadanymi plików GitHuba. Dowody CI: `development/publication-verification.json`. Testy sprzętowe, administracyjne i udana odpowiedź zewnętrznego AI nadal pozostają do wykonania.

## Aktualizacja zestawu 0.3.4 — 2026-09-15

445 testów przechodzi. PC Cleanup sprawdza brakujące pliki przed rollbackiem
i nie nadpisuje nowo utworzonego pliku docelowego. USB Toolkit sprawdza zapisaną
poprzednią wersję przed jej przywróceniem. Termux Setup zapisuje konfigurację
atomowo; Network Optimizer nie nadpisuje późniejszego trybu automatycznego DNS
i rozpoznaje ustawienia już przywrócone. Testy obejmują błędy i przerwania.
PC Cleanup/USB mają wersję 0.3.3, Termux Setup/Network Optimizer 0.3.4;
pozostałe wersje zachowano. Zestaw pozostaje wydaniem testowym.

## Aktualizacja zestawu 0.3.2 — 2026-09-15

Backup i Integrity Monitor podniesiono do 0.3.2; 24 pozostałe narzędzia pozostają
w 0.3.1. 434 testy przechodzą. Backup zapisuje complete dopiero po wszystkich
etapach, uwzględnia błędy manifestu i prowadzi dziennik restore. Integrity Monitor
nie traktuje UNKNOWN ACL/ADS jako sukcesu ani nie zastępuje takim odczytem baseline.
Nowe EXE przeszły cztery scenariusze odzyskiwania, w tym wymuszone przerwanie
procesu na plikach próbnych. Paczka ZIP i SHA256 zweryfikowane.

## Aktualizacja 0.3.1 — 2026-09-15

Wszystkie 26 projektów ma teraz wersję 0.3.1. Dodano pomiar GPU w czasie,
poprawiono okno pomiaru CPU, korelację procesów oraz wykrywanie zmiany MAC
na dodatkowym IP. GUI ma ograniczoną kolejkę i bufor, obsługuje strumień UTF-8,
zatrzymanie/restart oraz duże wyniki bez zawieszania zawijaniem długich wierszy.
Test 1,2 mln znaków, zatrzymania i ponownego uruchomienia przeszedł.
Przegląd zakresu i granic weryfikacji: `development/SPECIFICATION-AUDIT.md`.

26 EXE 0.3.1 zbudowano i sprawdzono: 78 kontroli uruchamiania oraz pięć
scenariuszy integracji EXE przeszło. 421 testów backendów i osiem integracji
CLI przechodzi. Zmiany zapisano w commitach wszystkich 26 repozytoriów.
Starszy ZIP 0.3.0 pozostaje
oddzielnym artefaktem. API nadal ma niepotwierdzoną odpowiedź (HTTP 429),
a testy sprzętowe/administracyjne i rzeczywisty run CI pozostają do wykonania.

## Aktualizacja desktop — 2026-09-15

Dodano GUI do 26 programów, panel, PDF i formularz serwisowy, opcjonalny OpenAI,
podpisy Ed25519, ACL/ADS, VSS, Firefox, wiele IP/MAC i live TCP SYN capture.
Źródła mają samodzielne skrypty budowy EXE i konfigurację CI (jeszcze bez runu GitHub).
Gotowa testowa paczka desktop 0.3.0 zawiera 26 EXE; ZIP i hashe zweryfikowano.
416 testów i 78 kontroli startu EXE przeszło. Panel wykrywa 24 narzędzia.
Numery backendów w oknach pozostają numerami
poprzednich wydań. Aktualne wyniki są w `development/*verification.json`.

Potwierdzono start 26 GUI, formularz SHA256, PDF wielostronicowy oraz podpisy
i PDF z EXE. API OpenAI zwróciło HTTP 429. VSS, live capture, naprawy i fizyczny
Android wymagają testów docelowych. Pozostaje końcowe wersjonowanie, przegląd
specyfikacji i dłuższe próbkowanie GPU.

Poniższa tabela przedstawia historyczny stan MVP 0.2, a nie aktualną listę braków.

## Historyczny stan MVP 0.2

Stan: 2026-09-14. Autor: Dominik Wasilak. Wszystkie 26 projektów ma samodzielną
wersję MVP na licencji MIT, dokumentację, testy i lokalne repozytorium Git.
Dashboard i CLI powstały na końcu i uruchamiają istniejące programy.
Nie jest to pełna implementacja wszystkich szczegółów pierwotnej specyfikacji.

| Kolejność | Projekt | Działający zakres MVP | Istotne dalsze prace |
|---|---|---|---|
| 1 | Windows Toolkit | Odczyt, historia/szukanie aktualizacji, test sieci, cache/kosz, naprawy i rollback kwarantanny | Testy napraw w VM i uprawnień administratora |
| 2 | Security Check | Odczyt i reguły 21 kategorii, coverage UNKNOWN, scoring | Testy różnych polityk/wersji Windows |
| 3 | Internet Diagnostic | ICMP/DNS/MTU/trasa, DHCP/DNS/interfejsy, Wi-Fi | Pomiar RSSI Windows jest szacunkiem; testy sterowników i Linux |
| 4 | DNS Benchmark | Autodetekcja system/router/public, UDP i TCP fallback | Testy IPv6 i różnych resolverów |
| 5 | Termux Setup | Pakiety, PATH/aliasy, Git/SSH opt-in i backup/rollback | Test fizycznego Termuxa |
| 6 | ADB Diagnostic | SoC, bateria/RAM/storage, pakiety, uprawnienia, grupy logcat | Test urządzeń/OEM |
| 7 | Malware Triage | Procesy/hash/podpisy, rejestr, korelacja persistence, liczniki GPU, Chromium, Trust Check | GPU jest próbką chwilową; kolejne reguły i formaty rozszerzeń |
| 8 | File Inspector | Wymagane hashe, entropy, metadane, MIME, strings opt-in, PE, podpis | Dalsze formaty są rozszerzeniem zakresu |
| 9 | Hash Checker | Plik/folder/manifest, verify/compare i bezpośrednie compare-folders | Podpisy manifestów są opcjonalnym rozszerzeniem |
| 10 | Backup | Foldery użytkownika, eksporty aplikacji/sterowników/konfiguracji, zakładki Chromium, SHA256 i restore | Test eksportu sterowników, inne przeglądarki; VSS/ACL opcjonalne |
| 11 | PC Cleanup | TEMP, cache DirectX/miniatur, analiza kosza/logów/Downloads/instalatorów i rollback | Kosz jest analizowany; trwałe opróżnianie osobno w Windows Toolkit |
| 12 | System Snapshot | 12 kategorii, programy 32/64-bit/użytkownika, różnice według identyfikatorów | Testy innych wersji Windows i zmian sprzętu |
| 13 | NetRadar | Przyrostowe logi, SYN, whitelist/ignore, limity pamięci, historia i rotacja | Brak przechwytywania pakietów; retransmisje mogą zawyżać próby |
| 14 | LAN Radar | Cache/import i ICMP discovery, SQLite, OUI, reverse DNS, historia | ICMP nie dowodzi offline; wiele IP tego samego MAC nadal ograniczone |
| 15 | Nmap Profiles | Sześć profili, plan/wykonanie, XML i porównanie | Test docelowego Nmap/Npcap; nazwy hostów są rozszerzeniem |
| 16 | Network Optimizer | DNS/MTU z backup/rollback, ICMP DF, odczyt TCP/NIC/IPv4/IPv6/cache | Zmiany TCP/NIC/IPv6 wymagają konkretnego uzasadnienia; routing sond jest systemowy |
| 17 | Network Snapshot | Cache/import lub ICMP, OUI/nazwy, snapshoty i różnice hostów | Obserwacja nie jest pełnym wykryciem; wiele IP tego samego MAC nadal ograniczone |
| 18 | Android Inspector | Metadane/uprawnienia, appops, wskazania Device Admin, coverage ról | Fizyczne urządzenia/OEM; label zasobu APK może pozostać UNKNOWN |
| 19 | Folder Watch | Polling i natywne Windows events, SHA256, SQLite, wykrywanie overflow | Linux polling; hash krótkotrwałego pliku może być UNKNOWN |
| 20 | Integrity Monitor | Baseline/check/update po zgodzie, backup baseline | Podpisy i ACL/ADS są opcjonalnym rozszerzeniem |
| 21 | USB Toolkit | Struktura, kopie, SHA256, aktualizacja wersji i rollback, zachowanie raportów | Test rzeczywistego nośnika; przerwanie zasilania wymaga kontroli dziennika |
| 22 | Repair Report | Wszystkie pola, walidacja, HTML/JSON/TXT | PDF tylko na osobne żądanie |
| 23 | Termux Toolkit | Osiem kategorii i podoperacje, backup tar z SHA256/verify | Fizyczny Termux/Termux:API |
| 24 | AI Diagnostic Assistant | LOCAL MODE, szersza normalizacja raportów, reguły, źródłowe alerty i scoring | Zewnętrzny provider opcjonalny; brak kalibracji progów dla wszystkich urządzeń |
| 25 | Dashboard | Wymagane polskie menu, 24 narzędzia, podprocesy i ustawienia | Bogatszy TUI jest opcjonalnym rozszerzeniem |
| 26 | CLI | Instalowalna komenda prestige, forwarding, kody wyjścia | Instalacja CLI nie instaluje backendów ani pozostałych projektów |

## Weryfikacja

- 391 testów oraz 26 testów uruchomienia: development/verification.json — PASS.
- Wheel CLI zainstalowany w izolowanym venv, 8 testów integracji — PASS.
- Rzeczywisty odczyt Windows Toolkit, Security Check, Malware Triage i Network Optimizer.
- Malware Triage: odczyt 20 sekcji i korelacja procesów; brak modyfikacji systemu.
- Natywny Folder Watch: rzeczywiste create/delete chwilowych plików testowych na Windows.
- ICMP DF na loopback: 10/10 odpowiedzi. DNS: lokalne serwery UDP i TCP fallback.
- Naprawy, zmiany konfiguracji, czyszczenie, backup/restore i aktualizację USB sprawdzano
  na atrapach backendów lub danych syntetycznych. Nie wykonano tych operacji na danych użytkownika.
- Testy Android/Termux/Nmap, uprawnień administratora, różnych OEM i macierzy systemów pozostają.

## Wydanie zestawu 0.2.0

20 projektów rozszerzono do 0.2.0. Sześć projektów bez zmian zachowuje 0.1.0.
Nowa paczka dist/prestige-tech-0.2.0.zip obejmuje bieżące wersje wszystkich 26 projektów.
Stara paczka 0.1.0 pozostaje bez zmian. Sumy obu wydań: dist/SHA256SUMS.txt.
Licencja MIT jest obecna i zgodna w każdym projekcie. Nie dodano wyłączonych projektów ani monolitu.

Zestaw działa lokalnie, lecz nie jest oznaczony jako w pełni zweryfikowany produkcyjnie.
Tabela rozdziela pozostałe ograniczenia od opcjonalnych rozszerzeń. Szczegółowe komendy
oraz zakres dostępności backendów: README i docs/USAGE.md każdego narzędzia.
