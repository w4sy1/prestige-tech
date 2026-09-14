# Prestige Tech — stan realizacji

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
