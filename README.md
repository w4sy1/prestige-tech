# PRESTIGE TECH
by Dominik Wasilak

Zestaw **26 samodzielnych projektów (0.1.0 / 0.2.0)**: diagnostyka, administracja,
monitoring, integralność, Android i raporty. Wszystkie na licencji MIT.

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
Programy Python nie wymagają pakietów pip. Wybrane funkcje wymagają backendów:
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

Wynik: **391 testów**, 26 testów uruchomienia i 8 testów integracji instalowanej
komendy CLI. Weryfikacja na Windows z Python 3.14 i PowerShell 7. Nie wykonano pełnej
macierzy wersji Python ani testów fizycznych urządzeń Android/Termux.

## Prywatność i bezpieczeństwo

Raporty/logi pozostają lokalne. Ping, DNS i Nmap wykonują ruch po świadomym wywołaniu.
Nie ma zewnętrznego providera AI ani telemetrii. Raporty mogą zawierać prywatne dane.
Czyszczenie TEMP używa kwarantanny. SFC/DISM/Winsock nie mają gwarantowanego rollbacku;
snapshot diagnostyczny nie jest kopią systemu. Heurystyki nie są werdyktem malware.

## Autor, licencja i wsparcie

Dominik Wasilak — Prestige Tech — prestigetech@gmail.com. Licencja MIT.
Opcja wsparcia autora zostanie udostępniona w przyszłości.
Każdy samodzielny projekt zawiera config/author.json.
