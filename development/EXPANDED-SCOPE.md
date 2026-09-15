# Rozszerzony zakres zatwierdzony przez użytkownika

## Najnowszy stan 0.3.2

Backup: naprawiony przedwczesny complete, sprawdzanie błędów/rozmiarów manifestu,
dziennik odtwarzania. Integrity Monitor: walidacja baseline, INCOMPLETE przy UNKNOWN
ACL/ADS i ochrona baseline przed niekompletną aktualizacją. 434 testy PASS.
Cztery scenariusze odzyskiwania z prawdziwych EXE PASS (tylko pliki próbne).
Paczka 0.3.2 zawiera dwie poprawione aplikacje i 24 niezmienione EXE 0.3.1.

## Najnowszy stan 0.3.1

Zamknięto: pomiar GPU w czasie, korelację z procesem, poprawkę CPU (hashowanie
nie zawyża okresu pomiaru), zmianę MAC dla dodatkowego IP, GUI pod dużym wyjściem,
testy stop/restart i spójne wersje 0.3.1. Pełniejszy przegląd 26 projektów zapisano
w SPECIFICATION-AUDIT.md. Zbudowano 26 EXE 0.3.1; 421 testów, 78 kontroli startu,
pięć integracji EXE i osiem integracji CLI przeszło. Commity 26 repozytoriów zapisane.
Poniższe statusy 0.3.0 są historyczne; nie traktować GPU/wersjonowania jako nadal brakujących.

## Aktualizacja 2026-09-15 (zastępuje statusy poniżej)

26 GUI i test formularza SHA256: PASS. Formularz serwisowy gotowy.
PDF: test 12 stron, Unicode i zachowania istniejącego pliku PASS.
Podpisy Ed25519 i eksport PDF sprawdzone również z EXE.
ACL/ADS sprawdzone na rzeczywistym pliku próbnym ze strumieniem NTFS.
VSS/ACL backupów, Firefox, wiele IP/MAC, nazwy hostów i IPv6 Nmap, live TCP SYN
i deduplikacja retransmisji zaimplementowane; testy backendów w większości używają atrap.
Konfiguracja CI i samodzielne build_exe.py dodane w 26 repozytoriach.
Prawdziwe żądanie AI miało klucz w środowisku i zwróciło HTTP 429.
Nie opisywać tego jako braku klucza. Integracja instalowanego CLI: 8 kontroli PASS.

Zakończono budowę 26 EXE i testowej paczki desktop 0.3.0. ZIP, SHA256,
78 kontroli startu EXE i wykrywanie narzędzi przez panel: PASS. 416 testów PASS.
Zmiany zapisane w lokalnych commitach 26 repozytoriów. Numery backendów nadal
0.1/0.2; końcowe wersjonowanie, dokumentacja, checkpoint i źródłowe wydanie pozostają.
Do dalszej pracy: pełniejsze testy interakcji/przerywania GUI, próbkowanie GPU,
przegląd szczegółów specyfikacji oraz testy docelowych urządzeń i uprawnień.
Poniższe sekcje zachowują historyczny plan z 2026-09-14.

2026-09-14: użytkownik zlecił wszystkie pozostałe funkcje, także opcjonalne, GUI, PDF,
zewnętrzne AI oraz docelowe osobne EXE i paczkę. Nie traktować kolejnego „kontynuuj” jako nowego zadania.

## W toku

- 26 niezależnych GUI Tkinter i wspólny panel: źródła dodane, pierwsze testy uruchomienia PASS.
- PDF z Unicode: generator w każdym projekcie, próbny raport wyrenderowany i sprawdzony wzrokowo.
- Zewnętrzne AI: OpenAI Responses, opt-in, klucz wyłącznie ze środowiska; brak prawdziwego połączenia bez klucza użytkownika.
- EXE: pojedyncze pliki PyInstaller z interpreterem. Pilot Hash Checker zbudowany i uruchomiony; przed końcowym wydaniem przebudować po dodaniu podpisów.
- Podpisy Ed25519: dodany moduł Hash Checker/Integrity Monitor, wymaga testów i dokumentacji.

## Pozostałe prace

- Testy 26 GUI, interakcji formularzy, procesów i ich przerywania; wizualna kontrola okien.
- Formularz raportu serwisowego i wygodny wybór narzędzi w panelu.
- Weryfikacja PDF wielostronicowych i eksportu z uruchomionych EXE.
- ACL/ADS i VSS; rozszerzenia reguł Malware Triage, wiele IP/MAC, poprawki monitoringu i pozostałych ograniczeń.
- Testy podpisów; klucze prywatne szyfrowane, nie trafiają do paczek.
- CI samodzielnych repozytoriów i powtarzalny build/pakowanie wszystkich EXE.
- Aktualizacja wersji/dokumentacji/licencji zależności, pełne testy, commity i nowa paczka.
- Testy wymagające fizycznego Androida/Termuxa, Nmap/Npcap, administracyjnej VM i klucza API pozostają osobno od testów atrap.

Pierwotne siedem wyłączeń projektów nadal obowiązuje. Nie publikować ani wysyłać wiadomości do innych bez odpowiedniego zlecenia.
