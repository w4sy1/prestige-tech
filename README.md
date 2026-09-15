# PRESTIGE TECH
by Dominik Wasilak

Zestaw **26 samodzielnych projektów — paczka 0.3.4 (wydanie testowe)**: diagnostyka, administracja,
monitoring, integralność, Android i raporty. Własny kod na MIT; zależności zachowują swoje licencje.

## Pobieranie z GitHuba

[Pełna paczka Windows EXE i źródła 0.3.4](https://github.com/w4sy1/prestige-tech/releases/tag/v0.3.4).
Wydanie jest oznaczone jako **Pre-release**. Pobierz `prestige-tech-desktop-0.3.4-windows-x64.zip`,
rozpakuj je i uruchom `prestige-tech-dashboard.exe` lub dowolny pojedynczy program.

To repozytorium zawiera dokumentację zestawu i skrypty budowania. Kod 26 programów
znajduje się w osobnych repozytoriach `w4sy1/prestige-*`; komplet źródeł ze strukturą
katalogów potrzebną do budowania zawiera załącznik `prestige-tech-0.3.4.zip` w wydaniu.
Automatyczny przycisk GitHuba „Source code” pobiera tylko zawartość tego repozytorium.

## Windows: interfejs graficzny

Wersje programów pozostają niezależne: Backup/Integrity 0.3.2, Cleanup/USB 0.3.3,
Termux Setup/Network Optimizer 0.3.4, pozostałe 0.3.1.
Rozpakuj `dist/prestige-tech-desktop-0.3.4-windows-x64.zip` i uruchom
`prestige-tech-dashboard.exe`. Każdy EXE jest również samodzielnym programem.
Python jest dołączony. PowerShell 7, ADB, Nmap i środowisko Termux pozostają
zewnętrznymi zależnościami dla odpowiednich funkcji.

Źródła GUI: `python prestige-tech-dashboard/gui.py`.
Budowa pojedynczego projektu: jego `docs/BUILD.md` i `build_exe.py`.
Pełną przebudowę obsługuje `development/build_desktop.py`; podaj `--version`
z nowym numerem paczki, aby zachować istniejące archiwa, oraz `--force`.
Przegląd wymagań i granic testów: [SPECIFICATION-AUDIT.md](development/SPECIFICATION-AUDIT.md).

## Szybki start

Wymagany Python 3.11+, a dla Windows Toolkit PowerShell 7.
Otwórz terminal w katalogu zestawu:

```powershell
python ./prestige-tech-dashboard/app.py
python ./prestige-tech-cli/app.py --list
python ./prestige-tech-cli/app.py files -- ./plik.exe
pwsh -NoProfile -File ./prestige-windows-toolkit/prestige.ps1 -Command collect -Modules disks
```

Każdy program ma README i docs/USAGE.md (Windows Toolkit: README).
Podstawowe backendy Python używają biblioteki standardowej. PDF wymaga
`requirements-gui.txt`, a podpisy `requirements-signing.txt`. EXE zawierają te zależności.
Wybrane funkcje wymagają backendów:
ADB, Nmap, ping, PowerShell, ip lub pakietów Termuxa.

## Komenda prestige

```powershell
python -m pip install ./prestige-tech-cli
prestige --tools-root "C:/sciezka/do/zestawu" --list
prestige --tools-root "C:/sciezka/do/zestawu" ai -- --input raport.json
```

Alternatywnie ustaw PRESTIGE_TOOLS_ROOT. Instalacja CLI nie instaluje innych narzędzi.
Launcher nie dodaje --apply/-Execute ani nie zatwierdza operacji za użytkownika.

## Stan i testy

[PROJECT-STATUS.md](PROJECT-STATUS.md) opisuje działający zakres i brakujące elementy.
To nie jest ukończona implementacja każdego punktu specyfikacji.
`python development/verify.py` uruchamia testy wszystkich samodzielnych projektów.

Wynik: **445 testów**, kontrole uruchomienia EXE, pięć scenariuszy integracji EXE
i osiem testów integracji instalowanej komendy CLI. Dodatkowo sprawdzono GUI
z dużym wynikiem, UTF-8 i zatrzymaniem/restartem procesu.
W 0.3.2 dodano cztery testy integracyjne odzyskiwania z EXE, w tym rzeczywiste
przerwanie backupu na plikach próbnych i weryfikację niekompletnego manifestu.
W 0.3.4 sprawdzono też odmowę rollbacku uszkodzonej kwarantanny oraz kopii USB
bezpośrednio z EXE. Błędy zapisu konfiguracji Termuxa i rollback sieci sprawdzono
lokalnie na plikach próbnych i atrapach, bez zmiany konfiguracji tego komputera.
Weryfikacja na Windows z Python 3.14 i PowerShell 7. Nie wykonano pełnej
macierzy wersji Python ani testów fizycznych urządzeń Android/Termux.

## Prywatność i bezpieczeństwo

Raporty/logi pozostają lokalne. Ping, DNS i Nmap wykonują ruch po świadomym wywołaniu.
AI domyślnie działa lokalnie. Opcjonalny provider OpenAI wysyła wybrane metryki
po jego wybraniu; GUI wymaga potwierdzenia wysłania. Klucz pochodzi ze środowiska
lub pamięci sesji. Nie ma telemetrii. Raporty mogą zawierać prywatne dane.
Czyszczenie TEMP używa kwarantanny. SFC/DISM/Winsock nie mają gwarantowanego rollbacku;
snapshot diagnostyczny nie jest kopią systemu. Heurystyki nie są werdyktem malware.

## Autor, licencja i wsparcie

Dominik Wasilak — Prestige Tech — prestigetech@gmail.com. Licencja MIT.
Opcja wsparcia autora zostanie udostępniona w przyszłości.
Każdy samodzielny projekt zawiera config/author.json.
