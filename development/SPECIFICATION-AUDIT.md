# Przegląd wymagań — 2026-09-15

Podstawa: SPECIFICATION.txt i późniejsze zlecenie GUI, PDF, zewnętrznego AI oraz EXE.
To przegląd implementacji i dostępnych testów, nie certyfikacja ani dowód działania
na każdej konfiguracji. Samo istnienie kolektora nie oznacza udanego odczytu na
każdym urządzeniu; raport powinien zachować UNKNOWN/PARTIAL.

| Program | Pokrycie w kodzie | Granica potwierdzenia |
|---|---|---|
| Windows Toolkit | Kolektory systemu, dysków, ochrony, sieci, procesów, autostartu, software i zdarzeń; osobne naprawy; scan/preview/clean; raporty | Naprawy, kosz, polityki i uprawnienia wymagają VM |
| Security Check | 21 kategorii, scoring, uzasadnienia i wskazanie dalszej kontroli | Reguły nie zastępują porównania z polityką organizacji |
| NetRadar | Firewall logs, SYN capture, częstotliwość, porty, whitelist, historia, deduplikacja | Live capture sprawdzone parserem syntetycznym, nie ruchem na docelowym interfejsie |
| LAN Radar | SQLite, kategorie, IP/MAC/hostname/vendor, historia i wiele IP | MAC na dodatkowym IP poprawiono w 0.3.1; cache i ICMP nie dowodzą offline |
| Nmap Profiles | Profile, autoryzowane cele, XML/TXT/JSON, porównanie, hostname i IPv6 | Potrzebny rzeczywisty Nmap; brak pełnego testu skanów |
| Internet Diagnostic | ICMP, DNS, jitter, trasa, MTU, interfejsy i klasyfikacja | RSSI Windows jest szacunkiem; ICMP może być ograniczany |
| Network Optimizer | Odczyt modułów; DNS/MTU before/backup/change/after/rollback | Nie proponuje zmian TCP/NIC/IPv6 bez mierzalnego powodu; routing sond wybiera system |
| DNS Benchmark | Wiele resolverów, serie zapytań, statystyki, timeout, TCP fallback | Potrzebne testy różnych operatorów i IPv6 |
| Termux Setup | Profile, pakiety, foldery, backup konfiguracji, Git/SSH opt-in | Wymaga fizycznego Termuxa |
| Termux Toolkit | Osiem kategorii, backendy systemowe, backup i weryfikacja | Windows EXE nie zapewnia środowiska Termux |
| ADB Diagnostic | Parametry urządzenia, pakiety, usługi, sieć i logcat bez zbędnych identyfikatorów | Testy OEM i urządzeń fizycznych |
| Android Inspector | Metadane, uprawnienia, appops, role i poziomy zainteresowania | Role i nazwa zasobu APK mogą być UNKNOWN |
| Backup | Foldery, manifest/hash, postęp, restore, eksporty, zakładki, VSS/ACL | VSS i odtwarzanie DACL wymagają VM; Firefox eksportuje zakładki bez hierarchii folderów |
| PC Cleanup | Scan/preview/clean, profile, analiza dużych plików i rollback | Dane osobiste nie są automatycznie usuwane; testy wariantów kosza Windows |
| Malware Triage | Kolektory, rejestr, persistence, przeglądarki, metadane plików i korelacja procesów | CPU/GPU w czasie poprawione w 0.3.1; wskaźniki nie są werdyktem malware |
| File Inspector | Metadane, hashe, MIME, entropy, strings opt-in, podpisy i PE | Bez wykonywania badanego pliku; nie jest pełnym parserem wszystkich formatów |
| Hash Checker | Hash, manifest, verify, compare i opcjonalne podpisy | Tożsamość klucza publicznego musi być potwierdzona osobno |
| Folder Watch | Polling, natywne Windows events, SQLite, hash, overflow | Bardzo krótkotrwały plik może pozostać bez hasha |
| Integrity Monitor | Baseline, różnice, potwierdzana aktualizacja, podpisy, ACL/ADS | Odczyt NTFS ADS sprawdzony na pliku próbnym |
| USB Toolkit | Struktura katalogów, kopie wskazanych narzędzi, manifest, wersje, rollback | Potrzebny test fizycznego nośnika i przerwania zasilania |
| Repair Report | Pola zlecenia, walidacja, formularz, HTML/JSON/TXT/PDF | PDF sprawdzono wizualnie oraz automatycznie na wielu stronach |
| System Snapshot | Kategorie wymagane w promptcie, snapshot i compare | Różne wersje Windows/sprzętu wymagają osobnych prób |
| Network Snapshot | IP/MAC/nazwa/vendor/status/czas, różnice, wiele IP | Status odzwierciedla metodę obserwacji, nie pewność dostępności |
| Dashboard | Menu kategorii i launcher osobnych programów, GUI panelu | Test odkrywania EXE i samodzielności; wymagane narzędzia zewnętrzne nadal oddzielne |
| AI Assistant | Normalizacja, lokalne reguły/scoring i OpenAI opt-in | Prawdziwe API zwróciło HTTP 429; odpowiedź modelu niepotwierdzona |
| CLI | Instalowalna komenda prestige, aliasy, forwarding i kody błędów | Wheel nie instaluje całej kolekcji backendów |

## Poprawki wynikające z bieżącego przeglądu

- Wielokrotne próbki GPU i korelacja PID zamiast pojedynczego odczytu.
- CPU mierzone przed hashowaniem, z kontrolą ponownego użycia PID.
- Korelacja aktywnych połączeń i autostartu z procesem.
- Zmiana MAC dla dodatkowych adresów IP.
- GUI: ograniczona kolejka/bufor, UTF-8 między porcjami, obsługa nadmiaru tekstu,
  zatrzymanie i ponowne uruchomienie, prawidłowe opcje nargs oraz append.
- Zgodne numery wersji 0.3.1, wheel i nowe EXE.

## Pozostające działania

Testy systemowe i sprzętowe z ostatniej kolumny, poprawna odpowiedź zewnętrznego
API, rzeczywisty run CI po publikacji oraz przegląd ergonomii z użytkownikiem.
Nie traktować testów atrap jako wykonania VSS, napraw Windows lub skanów Nmap.
Pierwotne siedem wyłączeń zachowano. Nie tworzono wspólnego monolitu ani
przedwcześnie wydzielonego prestige-tech-core.
