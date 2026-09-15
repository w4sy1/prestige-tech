# PRESTIGE TECH
by Dominik Wasilak

Zestaw **26 samodzielnych projektów 0.3.1 (wydanie testowe)**: diagnostyka, administracja,
monitoring, integralność, Android i raporty. Własny kod na MIT; zależności zachowują swoje licencje.

## Windows: interfejs graficzny

Rozpakuj `dist/prestige-tech-desktop-0.3.1-windows-x64.zip` i uruchom
`prestige-tech-dashboard.exe`. Każdy EXE jest również samodzielnym programem.
Python jest dołączony. PowerShell 7, ADB, Nmap i środowisko Termux pozostają
zewnętrznymi zależnościami dla odpowiednich funkcji.

Źródła GUI: `python prestige-tech-dashboard/gui.py`.
Budowa pojedynczego projektu: jego `docs/BUILD.md` i `build_exe.py`.
Pełny zestaw: `python development/build_desktop.py --version 0.3.1 --force`.
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

Wynik: **421 testów**, 78 kontroli uruchomienia EXE, pięć scenariuszy integracji EXE
i osiem testów integracji instalowanej komendy CLI. Dodatkowo sprawdzono GUI
z dużym wynikiem, UTF-8 i zatrzymaniem/restartem procesu.
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
