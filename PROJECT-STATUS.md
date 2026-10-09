# Prestige Tech — stan realizacji

Aktualna licencja własnego kodu: **Prestige Tech Free Use License** (`LICENSE`).
Wpisy historyczne poniżej opisujące MIT odnoszą się do wcześniejszych stanów
projektu i nie zastępują bieżącego pliku licencji.

Bieżący plik przekazania pracy i lista końcowych testów: `development/CONTINUE-HANDOFF.txt`.

## Etap 2026-10-09 — kod nocnego przeglądu

`python -m prestige_core.daily_schedule plan` pokazuje plan odczytowego
przeglądu. Rejestracja lub usunięcie zadania Windows wymaga osobnego
polecenia `install --confirm` albo `remove --confirm`; zadania nie
instalowano na komputerze użytkownika. Zadanie działa z uprawnieniami
bieżącego użytkownika po zalogowaniu, ma limit pięciu minut i nie wykonuje
napraw. Test jednostkowy sprawdza wygenerowany skrypt bez zmiany Harmonogramu.
Rzeczywiste uruchomienie o wyznaczonej godzinie pozostaje niezweryfikowane.

## Etap 2026-10-09 — wersje kopii i ważne strony

Storage & Recovery pokazuje listę bezpośrednich wersji kopii z liczbą plików
i stanem zapisu. Lista nie sprawdza sum; przywracanie nadal wymaga osobnego
wyboru i odtwarza do nowego folderu. Dashboard ma w obu stylach lokalne
skróty do maksymalnie sześciu stron HTTPS, z pełnym adresem i potwierdzeniem
przed otwarciem oraz możliwością usunięcia. Testy: Centra 327 uruchomionych,
326 OK, 1 pominięty; Dashboard 21 OK. Nie wykonywano rzeczywistego
odtwarzania danych ani otwierania stron banków w przeglądarce.

## Etap 2026-10-09 — odczytowe funkcje pomocy w Centrach

System Center odczytuje stan usługi drukowania i liczbę zadań, inwentaryzuje
urządzenia dźwięku oraz zapisuje jednorazowy przegląd do małego JSON. Nie
rozpoznaje jeszcze wyciszenia ani domyślnego wyjścia audio. Program
`python -m prestige_core.daily_checks --out KATALOG` umożliwia uruchomienie
tego przeglądu przez harmonogram; zadanie można teraz jawnie zarejestrować
osobnym poleceniem, ale nie wykonuje ono napraw. Security Center lokalnie
odczytuje zezwolenia
na powiadomienia w profilach Chrome/Edge, nie zmieniając ich. Network Center
oznacza odczytane słabe zabezpieczenia bieżącego Wi-Fi, lecz nie testuje hasła
routera. Report Center przygotowuje do podglądu i lokalnego zapisu prosty
raport dla bliskiej osoby z ostatnich 7 dni; niczego nie wysyła.

## Etap 2026-10-09 — pomoc w codziennych problemach

Rozbudowana koncepcja prostego systemu pomocy i mapa wszystkich nowych
pomysłów do istniejących Centrów są w `development/USER-HELP-DESIGN.md`.
Dodano odczytowy katalog czterech problemów, sygnalizator, rzeczywisty odczyt
wolnego miejsca oraz opakowanie istniejącej diagnostyki Internetu w
`prestige_core/senior_assistant.py`. To początek silnika planów, bez wykonania
napraw i harmonogramu. System Center ma teraz prosty wybór problemu z odczytem
wolnego miejsca; ścieżki dźwięku i drukarki uczciwie pokazują plan bez pomiaru.
Ochrona przeglądarki, sejf i zdalne SOS pozostają do zrobienia. Nie należy
przedstawiać tych funkcji jako gotowych.
Security Center ma lokalne sprawdzenie wpisanego adresu: pokazuje rzeczywistą
domenę, ostrzega o wybranych cechach i nie otwiera strony ani nie wysyła linku.
Brak ostrzeżeń nie oznacza, że strona jest bezpieczna; analiza treści,
reputacji i automatyczne ostrzeganie w przeglądarce pozostają do zrobienia.

## Etap 2026-10-09 — dostępność drugiego stylu i prostsze ścieżki

Drugi styl Dashboardu obejmuje teraz również pozostałe strony przez wspólną
paletę; wybór stylu niebieskiego przywraca jego kolory. Registry Manager pokazuje
po zapisaniu lub cofnięciu zmian prosty wynik: wykonana czynność, sprawdzenie
efektu, cofnięcie i informacja o ponownym uruchomieniu. Network Center ma
przycisk „Mam problem z Internetem”, który przygotowuje krótki pomiar i prowadzi
do planu naprawy bez automatycznego jej wykonania. Testy kodu Centrów:
297 uruchomionych, 296 zaliczonych, 1 pominięty; Dashboard: 19 zaliczonych.
Nie wykonywano rzeczywistych zmian w Windows, skanów sieci ani pomiarów na
urządzeniach. Katalog Registry nadal ma 20/600 zmian; pozostałych 580 nie
uznano za zweryfikowane. Klucz wydawcy i warunki edycji PRO są nadal otwarte.

## Etap 2026-10-08 — drugi wygląd Dashboardu według przesłanych grafik

Użytkownik dostarczył dwa obrazy referencyjne: główny Dashboard Prestige Tech
oraz System & Protection Center. W `prestige-tech-dashboard` drugi styl strony
głównej ma teraz górskie tło, czarno-złote menu, pięć głównych kafli, sekcję
stanu i baner. Kafle kierują do istniejących Centrów; nie pokazujemy
fikcyjnych procentów zdrowia, statusu ochrony ani historii z wizualizacji.
Niebieski styl pozostał dostępny. Zrzut działającego drugiego GUI:
`C:\Users\01dwa\Documents\PrestigeTech-Facebook\dashboard-drugi-gui.png`.
To odwzorowanie kierunku i układu, nie pikselowa kopia renderu referencyjnego.

## Etap 2026-10-08 — zabezpieczenia dla osoby nietechnicznej

Registry Manager zapisuje kopie zmian HKCU w lokalnym zarządzanym katalogu,
pokazuje ostatnie kopie i umożliwia podgląd/cofnięcie zakończonych zmian.
Odczyt i audyt osobno oznaczają wartość nieustawioną, odmowę dostępu i błąd.
Repair Report domyślnie drukuje status „niepotwierdzona”; status potwierdzony
wymaga jawnego wyboru i opisu testu końcowego. Obejmuje HTML/TXT/JSON/PDF.
Testy: 295 uruchomionych, 294 zaliczone, 1 pominięty. To testy kodu i GUI
offscreen; nie wykonywano prawdziwych zmian rejestru ani naprawy komputera.
Nadal otwarte: pozostałe punkty symulacji, 580/600 zmian Registry, rzeczywiste
testy Windows/urządzeń oraz warunki i klucz wydawcy edycji PRO.

## Etap 2026-10-08 — symulacja osoby nietechnicznej

Przeprowadzono symulację poznawczą użytkownika na podstawie GUI i kodu
Dashboardu oraz Centrów: `development/SENIOR-USER-SIMULATION.md`. To nie jest
badanie z udziałem seniorów ani potwierdzenie zachowania urządzeń. W Registry
Managerze przy minimalnym oknie tabela wyników miała tylko 7 px wysokości;
po zmianie układu i dodaniu przewijania offscreen smoke pokazuje co najmniej
170 px oraz brak przewijania poziomego. Potwierdzenia zmian zaczynają się od
skutku w zwykłym języku, a domyślna odpowiedź jest odmowna. Help rozróżnia
cel 600 zmian od odczytów ADMX. Priorytety P0/P1/P2 w dokumencie są propozycją
do wyboru z użytkownikiem, nie gotowymi funkcjami.

## Etap 2026-10-08 — audyt praktycznych zmian Registry Manager

Rozpoczęto weryfikację pomysłów z artykułu Hetman w
`development/REGISTRY-TWEAKS-AUDIT.md`. Artykuł jest inspiracją, a skutki i
zgodność ustalamy z dokumentacji Microsoft. Dodano cztery polityki HKCU z
kopią istniejącej lub nieistniejącej wartości, kontrolą edycji Windows,
podglądem i cofaniem oraz ShowStatusBar i trzema ustawieniami wyglądu
użytkownika oraz kolor akcentu pasków tytułu. Razem jest 20 zmian w kodzie.
Użytkownik potwierdził cel 200/200/200, czyli 600 unikalnych zmian;
580 pozostaje otwartych. Bez testów rzeczywistego zapisu Windows.
Pełna suita po tej iteracji: 286 testów, 285 PASS, 1 skip.
Na bieżącym komputerze polityki 012–015 odmawiają planu z uwagi na edycję
Windows niewymienioną przez Microsoft jako wspierana; ShowStatusBar odczytano
lokalnie jako istniejący DWORD. Wyścig zmiany przez inny proces przed zapisem
polityki jest teraz odmową bez nadpisywania obcej wartości.
Na życzenie użytkownika GUI ma sesyjny tryb eksperymentalny dla niewspieranej
edycji, domyślnie wyłączony i z ostrzeżeniem w planie/potwierdzeniu.
Zwykłe ustawienia motywu/przezroczystości działają niezależnie od tego trybu.

## Etap 2026-10-08 — Registry Manager dla początkujących i podział edycji

Registry Manager pokazuje krótkie opisy skutku, ryzyka i sposobu sprawdzenia
11 zmian HKCU Explorer (w tym 2 nowe: chronione pliki systemowe i ikona typu
na miniaturze). Trzy istniejące zmiany oznaczono FREE; pozostałe PRO i ich
zapis jest blokowany bez podpisanej licencji. Odczyt, plan i cofnięcie nadal
są dostępne bez PRO. Dodano weryfikację podpisu Ed25519 i ważności klucza
offline, lokalne narzędzie wydawcy oraz zapamiętanie ścieżki klucza klienta.
Prywatny klucz nie powstał i nie należy do repozytorium; publiczny klucz
wydawcy trzeba wygenerować i dołączyć przed wydaniem PRO. Obecna Prestige
Tech Free Use License mówi o darmowym korzystaniu z kompilacji, więc warunki
edycji płatnej wymagają osobnej aktualizacji przed dystrybucją. Docelowych
20/20/20 lub 50/50/50 zmian jeszcze nie ma. Zapisy testowano tylko na
symulowanym rejestrze, bez VM.
Macierz zamierzonego zakresu FREE/PRO dla całego zestawu jest w
`development/EDITION-MATRIX.md`; poza Registry Managerem bramki nie są jeszcze
wdrożone. Pełna suita po tym etapie: 280 testów, 279 PASS, 1 skip.

## Etap 2026-10-08 — uzupełnienie inwentaryzacji, Internetu i analizy miejsca

System Snapshot zbiera dodatkowo CPU, GPU, BIOS, dyski fizyczne i liczniki
niezawodności (w tym temperaturę, jeśli sterownik ją udostępnia). Stare
migawki v1 bez nowych sekcji nadal można wczytać; porównanie brakującej sekcji
oznacza UNKNOWN. Internet Diagnostic ma opcjonalne sondy HEAD HTTP/HTTPS do
example.com z limitem czasu, bez pobierania treści i bez śledzenia przekierowań.
PC Cleanup analizuje zajętość wybranego katalogu i największe pliki bez
uprawnienia do usuwania. Pomiary i nowe kolektory sprawdzono testami
symulowanymi; temperatury sprzętowe mogą być niedostępne.
Storage & Recovery odczytuje obecne urządzenia PnP USB z VID/PID i stanem;
lista obejmuje również koncentratory i peryferia, więc nie jest testem nośnika.
AI Center ma też lokalne połączenie 2–10 zapisanych raportów JSON w jedną
ocenę regułową z licznikami źródeł i SHA-256 plików. To fragment funkcji
iDiagnostics, bez ustalania pewnej przyczyny ani zdalnego dostępu.
Po tym etapie pełna suita ma 276 testów: 275 zaliczonych, 1 pominięty.

## Etap 2026-10-08 — USB tylko do odczytu przed obrazowaniem

Storage & Recovery ma kontrolowane ustawienie atrybutu read-only przez DiskPart
dla wybranego niesystemowego dysku USB. Backend porównuje numer, identyfikator
i rozmiar nośnika przed poleceniem oraz potwierdza IsReadOnly przez Get-Disk po
wykonaniu. GUI wymaga jawnego potwierdzenia, potem ponownego odświeżenia i
wyboru źródła przed istniejącym obrazowaniem RAW do nowego pliku `.img` na
innym dysku. Obraz jest weryfikowany SHA-256. Atrybut nie jest sprzętową
blokadą zapisu; realnego pendrive'a i administratora nie testowano.

## Etap 2026-10-08 — kolejne funkcje Centrów i drugi widok Dashboardu

Network Center ma kartę „Naprawa sieci” dla flush DNS, odnowienia DHCP i
resetu Winsock. Korzysta ze wspólnego backendu System Center: plan przed
wykonaniem, wybór katalogu dziennika, osobne potwierdzenie i odczyt historii.
Operacje wymagają administratora i nie mają gwarantowanego cofnięcia.
Potwierdzenie odmowne sprawdzono testem GUI; realnych napraw nie uruchamiano.

Dashboard (`prestige-tech-dashboard`) ma drugi widok strony głównej oparty na
tym samym katalogu 10 Centrów oraz wybór stylu zapisywany w ustawieniach.
Oryginalny niebieski widok pozostaje dostępny. Nowego widoku nie nazywamy
odwzorowaniem 1:1, ponieważ brak obrazów referencyjnych.

Network Center pokazuje listę kopii DNS IPv4/IPv6 z wybranego katalogu.
Ma też odczytowy raport LAN HTML, sesyjny harmonogram ICMP z wyborem podsieci,
potwierdzeniem i limitem oraz zmianę listy zaufanych urządzeń Sentinel z kopią
i warunkowym cofnięciem. Zmiana zaufania wyłącza automatyczną ochronę sesji.
Monitor filtruje historię według ścieżki, rodzaju zdarzenia i czasu UTC.
Porównuje dwa rozłączne okresy zapisanych zdarzeń bez zmiany baseline oraz
zapisuje profile skanu/pollingu z wykluczonymi podfolderami. Tryb natywny jest
wyłączony przy aktywnych wykluczeniach, bo nie stosuje tego samego filtra.
Registry Manager pokazuje plan cofnięcia wartości HKCU przed potwierdzeniem
i zapisuje różnicę wartości z kopii oraz bieżącego odczytu do pliku JSON.
Storage & Recovery pokazuje dysk docelowy i wolne bajty przed obrazowaniem;
backend nadal ponawia kontrolę źródło–cel i miejsca przed zapisem.
Android Center zapisuje migawkę aplikacji i porównuje dwa wyniki offline,
również uprawnienia. Security Center porównuje zakres dwóch audytów offline
i zapisuje ostatni audyt do nowego JSON.
System Center pokazuje metadane dzienników napraw bez treści diagnostycznej.
Termux Center ma odczytowy przegląd środowiska i porównanie pakietów profilu
Setup z wynikiem `dpkg-query`, bez instalacji. Ostatni odczyt stanu można
zapisać jako nowy JSON. AI Center zapamiętuje tryb
„tylko lokalnie”. Report Center sprawdza wymagane pola oraz zapisuje manifest
SHA-256 wskazanych plików bez kopiowania załączników.
Report Center importuje także zapisane JSON z dziewięciu Centrów (Network,
Monitor, Registry, Storage, Android, Security, System, Termux i AI), gdy plik
odpowiada rozpoznanemu formatowi. Dodaje wyłącznie neutralny opis i odniesienie
do manifestu; źródło jest ponownie sprawdzane przed zapisem. Nie wypełnia
diagnozy ani testu końcowego. Nie wszystkie Centra mają osobny przycisk
eksportu tego wyniku, więc nie jest to automatyczne zasilanie raportu.
Bieżący wynik skanu LAN, historia zdarzeń Monitora, audyt Registry,
podsumowanie utworzonej kopii Storage, lista aplikacji Android,
odczyt środowiska Termux i analiza AI mogą teraz otworzyć bezpośrednio
formularz Repair Report. Przekazywany
jest tylko neutralny opis czynności; bez automatycznego zapisu pliku, diagnozy
i testu końcowego. Zmiana źródła lub modelu AI usuwa poprzedni wynik z okna.
System i Security Center mają wcześniejsze wejścia do Report. Żadne z tych
wejść nie obejmuje jeszcze wszystkich operacji danego Centrum.

Pełna suita `prestige-tech`: 267 testów, 266 zaliczonych i 1 pominięty.
Suita `prestige-tech-dashboard`: 18 testów zaliczonych. Dane urządzeń i
zmiany systemowe w testach były symulowane.

To są częściowe funkcje; nie zamykają całej listy rozbudowy. Testy na telefonie,
realne zmiany systemu/sieci/dysku i wydanie EXE pozostają otwarte.

## Etap 2026-10-07 — DNS IPv6 w Network Center

Dodano osobny plan, zapis DNS IPv6 z nową kopią JSON, odczyt kontrolny i
warunkowe cofnięcie. GUI pozwala wybrać rodzinę IPv4/IPv6. Zapis IPv6 używa
poleceń `netsh interface ipv6`, żeby nie zmieniać listy IPv4. Pełna suita:
240 testów, 239 PASS, 1 skip; źródłowy smoke Network Center PASS. Testy
potwierdzają logikę na symulowanym backendzie, nie rzeczywistą zmianę DNS
ani rollback na interfejsie Windows z uprawnieniami administratora.
Drugi styl Dashboardu i brakujące funkcje pozostałych Centrów pozostają otwarte;
dostępny opis referencyjnego wyglądu nie zawiera obrazów do odwzorowania 1:1.

## Etap 2026-09-30 — lokalne archiwum i porządek GitHub

Na życzenie właściciela zakończono migrację starych repozytoriów jako kierunek
pracy. 19 wciąż istniejących osobnych repozytoriów `prestige-*` zapisano
lokalnie jako lustra Git, paczki bieżących plików oraz komplet 114 załączników
z 19 wydań. Po weryfikacji kopii usunięto te 19 repozytoriów z GitHuba.
`w4sy1/prestige-tech` i `w4sy1/prestige-tech-dashboard` pozostają. Lokalne
katalogi źródłowe zachowano. Katalog GUI Dashboardu ograniczono do 10 nowych
Centrów bez zmiany układu i motywu; historyczny launcher CLI i stare EXE
w dawnych wydaniach pozostają jako materiały archiwalne.
Archiwum: `C:\Users\01dwa\Documents\PrestigeTech-Legacy-Archive-2026-09-30`.
Historyczne wpisy poniżej opisują stan sprzed tej decyzji.

## Etap 2026-09-30 — import migawki Network Snapshot

Network Center zapisuje teraz nową migawkę z jawnie wybranej listy JSON
urządzeń LAN, również bez wcześniejszego odczytu adapterów. Waliduje MAC/IP,
nie skanuje sieci, nie nazywa importu pełną obserwacją ani stanem online i
odmawia nadpisania istniejącej migawki. Audyt starych komend potwierdził
odpowiedniki LAN `observe/discover/list/history/tag`; Snapshot `capture` z
cache/skanu/importu oraz `compare`; DNS `state/profiles/run/system-test`.
Nadal brak m.in. konfiguracji DNS IPv6, listy kopii DNS oraz funkcji
zarządzania/autostartu/raportu HTML Sentinel.
Suita: 237 testów uruchomionych, 236 PASS, 1 skip.

## Etap 2026-09-30 — DNS Center i import obserwacji LAN

Network Center ma odczyt konfiguracji DoH Windows, ograniczony czasowo test
systemowego resolvera DNS oraz opcjonalną lokalną historię statystyk benchmarku
w SQLite. Import listy urządzeń LAN z JSON obsługuje oznaczenie obserwacji jako
pełnej wyłącznie po potwierdzeniu; brak urządzenia w takiej liście oznacza
„niezaobserwowane”, a nie offline. Testy wykonano na danych symulowanych;
rzeczywiste DoH, DNS, sieć i VM pozostają niezweryfikowane.
235 testów uruchomionych: 234 PASS, 1 skip.

## Etap 2026-09-30 — DNS i migawka wykrywania

Network Center dodaje do benchmarku publicznych DNS wykryte adresy z
konfiguracji adapterów; brama jest osobną opcją z ostrzeżeniem, że może nie
obsługiwać DNS. Ostatni wynik jawnego skanu wzbogaca zapisywaną migawkę
urządzeń i metadane discovery, bez twierdzenia, że cache dowodzi obecności
online. Sentinel porównuje jawny skan z pełnymi listami znanych/zaufanych:
nowe urządzenie, zmiana IP i możliwa zmiana MAC są tylko sygnałami do
sprawdzenia, bez blokady. Porównano kod DNS Center, LAN Radar, NetRadar i
Sentinel ze starymi źródłami w `development/FUNCTION-PARITY-AUDIT.md`.
227 testów uruchomionych, 226 PASS, 1 skip. Prawdziwych zapytań DNS,
Nmap/TShark, zmian Firewalla i
DNS/MTU nie wykonywano; nowe EXE nadal niezweryfikowane.

## Etap 2026-09-29 — kolejne odczyty Windows Toolkit

System Center ma teraz 14 sekcji odczytowych Windows Toolkit. Dodano firmware,
numer seryjny BIOS, uptime, aktywację Windows, nazwy i obecność wartości
Run/RunOnce oraz ostatnie zdarzenia System/Application. Wartości autostartu
nie są wyświetlane. Składnia wszystkich 14 zapytań PowerShell PASS; suita
222 uruchomione, 221 PASS, 1 skip. Nowych odczytów nie testowano na żywym
Windows. Pełny parytet pól oraz właściciel/podpis procesów nadal otwarte.

## Etap 2026-09-29 — diagnostyka Windows i wykrywanie sieci

Network Center pokazuje obok odpowiedzi ICMP wpisy cache sąsiadów w tej
samej lokalnej podsieci, oznaczone jako obserwacja o nieznanej dostępności.
System Center rozszerzono o odczyt dostępnych aktualizacji, dysków fizycznych,
liczników SMART i partycji (razem osiem sekcji Windows Toolkit). Porównano
backend Termux Setup/Toolkit ze starymi źródłami: logika jest taka sama;
testu fizycznego Termuxa nie wykonano. 221 uruchomionych, 220 PASS, 1 skip.
Pełny parytet Sentinel oraz pozostałych kolektorów Windows Toolkit,
rzeczywiste naprawy i test EXE nadal pozostają otwarte.
Opcjonalny Nmap `-sn -n` uzupełnia obserwacje wyłącznie w wybranej prywatnej
podsieci do /24. Osobno oznaczono wyniki Nmap, ICMP i cache. Test fixture
PASS; prawdziwego Nmap nie uruchamiano. 222 uruchomione testy, 221 PASS,
1 skip.

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

Opublikowano instalator Dashboardu v1.1.3 jako GitHub Release
`dashboard-v1.1.3`; jego 67 901 734 bajty i SHA-256 zweryfikowano z metadanymi
zdalnego assetu. Dashboard.exe i Launcher.exe przeszły smoke test z kodem 0,
17 testów Dashboardu PASS, kompilacja Inno Setup PASS. Manifest self-update
wskazuje to wydanie. Pełnego testu instalacji/aktualizacji w osobnej VM nie
wykonano. Ekran „Aktualizacje” liczy stare moduły i nadal może pokazywać
0; aktualizacja samego Dashboardu jest sprawdzana przez Launcher przy starcie.
CI Dashboardu po normalizacji ścieżek testu PASS na Pythonie 3.11 i 3.14.
Instalator nie zawiera nowego EXE Security Center; karta Centrum z kodu
wymaga sąsiedniego checkoutu `prestige-tech`.

Dashboard pokazuje teraz w opisach osobno aktualną inspekcję w Security
Center i starszy samodzielny File Inspector. Obie pozycje pozostały w
katalogu; test uruchomienia źródłowego Centrum i lokalnego starego EXE oraz
pełna suita Dashboardu przeszły. Wygląd Dashboardu nie był zmieniany.

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
