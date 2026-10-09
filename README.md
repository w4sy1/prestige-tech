# PRESTIGE TECH
by Dominik Wasilak

PRESTIGE TECH rozwija 26 samodzielnych narzędzi w połączone Centra. Stare
repozytoria i wydania pozostają dostępne jako historia projektu. Obecny kod
źródłowy Centrów jest wersją testową. Nowa paczka EXE przeszła testy startu,
lecz operacje na urządzeniach i zmiany systemowe wymagają osobnej weryfikacji.

Własny kod jest udostępniony na [Prestige Tech Free Use License](LICENSE).
Zależności i czcionki zachowują swoje odrębne licencje.

## Nowe Centra — kod źródłowy

| Obszar | Program | Uruchomienie |
|---|---|---|
| Sieć | Network Center | `python network_center.py` |
| Pliki i integralność | Monitor | `python monitor.py` |
| Rejestr Windows | Registry Manager | `python registry_manager.py` |
| Dyski i odzyskiwanie | Storage & Recovery | `python storage_center.py` |
| Android | Android Center | `python android_center.py` |
| Bezpieczeństwo | Security Center | `python security_center.py` |
| System Windows | System Center | `python system_center.py` |
| Termux | Termux Center | `python termux_center_gui.py` |
| Analiza | AI Diagnostic Assistant | `python ai_center.py` |
| Raporty | Repair Report | `python report_center.py` |

Windows, Python 3.11+ i PySide6 są wymagane dla GUI. Wybrane funkcje wymagają
ADB, Nmap, PowerShell lub uprawnień administratora. Po sklonowaniu tego repo
uruchom w nim `python -m pip install -e ".[gui,pdf,signing]"`, a potem wybrane
Centrum. Test okna bez urządzeń: `python network_center.py --smoke`.

[Dashboard](https://github.com/w4sy1/prestige-tech-dashboard) uruchamia Centra
z kodu, gdy oba repozytoria są w sąsiednich katalogach. W paczce Windows
wykrywa też dziesięć EXE w folderze `centers/`. Skrypt `build_centers.py`
buduje je na Windows z Pythonem 3.13, PyInstaller i zależnościami z
`.[gui,pdf,signing]`. Po lokalnej budowie paczkę składa skrypt
`package_desktop.py` w repozytorium Dashboardu. Archiwalne wydanie 0.3.4
nie zawiera obecnych Centrów.

[Stan funkcji i ograniczenia](PROJECT-STATUS.md) ·
[Macierz migracji](development/CENTER-MIGRATION-MATRIX.md) ·
[Katalog starych programów](PROGRAMS.md)

## Archiwalna paczka 0.3.4

[Pełna paczka Windows EXE i źródła 0.3.4](https://github.com/w4sy1/prestige-tech/releases/tag/v0.3.4).
Wydanie jest oznaczone jako **Pre-release**. Pobierz `prestige-tech-desktop-0.3.4-windows-x64.zip`,
rozpakuj je i uruchom `prestige-tech-dashboard.exe` lub dowolny pojedynczy program.

Wydanie 0.3.4 zawiera dokumentację zestawu i skrypty budowania. Kod 26 programów
znajduje się w osobnych repozytoriach `w4sy1/prestige-*`; komplet źródeł ze strukturą
katalogów potrzebną do budowania zawiera załącznik `prestige-tech-0.3.4.zip` w wydaniu.
Automatyczny przycisk GitHuba „Source code” pobiera tylko zawartość tego repozytorium.

[Lista wszystkich 26 programów: repozytoria i pojedyncze EXE](PROGRAMS.md).

## Windows: interfejs graficzny paczki 0.3.4

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

Dominik Wasilak — Prestige Tech — prestigetech@gmail.com. Własny kod:
[Prestige Tech Free Use License](LICENSE).
Opcja wsparcia autora zostanie udostępniona w przyszłości.
Każdy samodzielny projekt zawiera config/author.json.
