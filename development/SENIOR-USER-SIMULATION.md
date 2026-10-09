# PRESTIGE TECH — symulacja obsługi przez osobę nietechniczną

Stan: 2026-10-08. To **symulacja poznawcza na podstawie kodu i okien GUI**,
nie badanie z udziałem seniorów ani test rzeczywistych urządzeń. Nie dowodzi,
że każda opisana pomyłka wystąpi. Jej celem jest wybranie następnych funkcji
ochronnych z użytkownikiem, zanim powstaną nowe przyciski zmieniające system.

## Postać i zadanie

Pani Maria, 72 lata, zna przeglądarkę, zdjęcia i pocztę. Nie rozróżnia
rejestru, DNS, dysku fizycznego i litery dysku. Korzysta z Windows Home na
laptopie, bez uprawnień administratora; powiększa tekst i nie pamięta, gdzie
zapisała plik JSON. Cel: „Internet wolno działa, chcę to bezpiecznie naprawić
i wydrukować wynik dla serwisanta”. Ma na pendrivie zdjęcia rodzinne. W tym
scenariuszu nie wolno utożsamiać kliknięcia „Tak” ze zrozumieniem ryzyka.

## Spacer po obecnych przepływach

| Etap | Prawdopodobna pomyłka i skutek | Co kod już chroni | Luka do wyboru funkcji |
|---|---|---|---|
| Dashboard | Wybiera Registry Manager zamiast diagnostyki Internetu, bo słyszała, że „rejestr przyspiesza”. | Centra mają odrębne nazwy. | Jedna ścieżka „Mam problem z Internetem” prowadząca od odczytu do planu. |
| Registry — odczyt | Widzi „niedostępne” przy nieustawionej polityce i myśli, że system jest uszkodzony. | Audyt nie zapisuje wartości; rozdziela dostępne i niedostępne. | Osobne komunikaty „nieustawione”, „brak uprawnień” i „błąd”. |
| Registry — wybór | Uważa, że ukrycie Centrum powiadomień przyspieszy komputer; po zmianie może przeoczyć ostrzeżenie. | Opis skutku, PRO, kopia, potwierdzenie, oznaczony tryb eksperymentalny. | Odrębna etykieta „wygoda, nie przyspieszenie” i stopień ryzyka. |
| Registry — kopia | Zapisuje JSON w Pobranych, a później usuwa plik „bo nie wie, co to”. Nie potrafi cofnąć zmiany. | Zapis `open("x")` odmawia nadpisania istniejącej kopii; rollback weryfikuje jej treść. | Zarządzany katalog kopii i lista „moje ostatnie zmiany” z podglądem cofnięcia. |
| Registry — wynik | Odczytuje `0 → 1` jako kod błędu; nie wie, czy trzeba ponownie uruchomić Eksplorator/Windows. | Opisy w prostym języku i wskazówka „po zmianie”. | Ekran końcowy: „co zrobiono / jak sprawdzić / jak cofnąć / czy wymagany restart”. |
| Network — DNS | Wybiera adapter VPN lub wirtualny zamiast Wi‑Fi, traci połączenie albo nie widzi efektu. | Wybór interfejsu, plan, kopia i warunkowy rollback. | Rozpoznanie aktywnego adaptera i pokazanie go zwykłą nazwą przed zapisem. |
| Network — MTU | Zmienia liczbę, bo większa „musi być szybsza”; część stron przestaje działać. | Sonda DF, plan, kopia i warunkowy rollback. | Ukryć ręczne MTU za trybem eksperta; pokazać oczekiwany efekt i niepewność pomiaru. |
| Network — skan | Skanuje niewłaściwą sieć lub interpretuje brak odpowiedzi ICMP jako awarię urządzenia. | Limit prywatnej podsieci i oznaczenia dowodów/UNKNOWN. | Widok „urządzenie nie odpowiedziało ≠ jest wyłączone” oraz cel skanu po ludzku. |
| Storage — USB | Myli dysk numer 2 z literą E:, wskazuje pendrive ze zdjęciami jako cel obrazu. | Blokada dysku systemowego, sprawdzenie ID/rozmiaru, źródło ≠ cel, wolne miejsce. | Karty „Z TEGO kopiuję” i „TUTAJ zapisuję”, model/pojemność/zdjęcie poglądowe, dodatkowy test wyboru. |
| Storage — read-only | Uważa programowy atrybut read-only za sprzętowy write blocker i wyjmuje nośnik w trakcie obrazu. | GUI wyraźnie mówi, że to nie blokada sprzętowa; obrazowanie wymaga ponownego wyboru. | Po zakończeniu instrukcja bezpiecznego odłączenia i stan „programowo tylko do odczytu”. |
| System — naprawa | Kliknięcie SFC/DISM traktuje jak zwykły test; zamyka okno po kilku minutach. | Osobny plan, zgoda, dziennik, komunikat o braku gwarantowanego cofnięcia. | Rozdzielić „sprawdź” od „napraw”, czas/etapy i ostrzeżenie przed zamknięciem. |
| System — czyszczenie | Uznaje „duży plik” za zbędny i usuwa własny film lub dane aplikacji. | Analiza zajętości jest odczytowa; inne czyszczenie ma podgląd/kwarantannę. | Kategorie „moje pliki” zawsze wyłączone z automatycznych sugestii; jasny czas retencji kwarantanny. |
| Monitor | Wybiera cały dysk C:, potem widzi wiele odmów dostępu i uznaje je za wirusy. | Statusy błędów i ograniczeń, profile wykluczeń. | Kreator wyboru wąskiego folderu oraz wyjaśnienie „brak dostępu nie znaczy infekcja”. |
| Android/Termux | Nie zatwierdza debugowania na telefonie lub nie rozumie komunikatu ADB; ponawia akcję. | Wybór urządzenia i odczyty bez instalacji w większości przepływów. | Obrazkowa instrukcja na telefonie i prosty stan: „czekam na zgodę / kabel / urządzenie”. |
| Security | „Podejrzane” odczytuje jako „na pewno wirus”, ręcznie usuwa plik systemowy. | Audyt i analiza nie usuwają pliku automatycznie. | Wyniki z poziomem pewności, źródłem dowodu i bez przycisku „usuń” przy samym heurystycznym sygnale. |
| AI | Naciska „zewnętrzne AI”, nie rozumie kosztu i danych zawartych w logach. | Podgląd przesyłanych metryk, tryb lokalny i potwierdzenie wysłania. | Podświetlenie danych osobowych i kosztu przed zgodą; domyślnie lokalnie. |
| Report | PDF z napisem „wynik” traktuje jak potwierdzenie, że komputer jest naprawiony. | Formularz pokazuje brakujące pola; nie wpisuje automatycznie diagnozy i testu końcowego. | Wydrukowane oznaczenie „diagnoza niepotwierdzona”, jeśli nie ma testu po naprawie. |

## Wynik 10-minutowego przejścia bez urządzeń

1. **Potwierdzony problem układu Registry GUI:** przy minimalnym oknie
   820×560 tabela miała tylko 7 px wysokości. Po dodaniu przewijania i
   podziale długich rzędów ma co najmniej 170 px i poziomy pasek przewijania
   nie jest potrzebny w offscreen smoke. To test geometrii, nie ocena czcionek
   na ekranie użytkownika.
2. **Potwierdzony problem słownictwa:** wcześniejsze okno potwierdzenia
   zaczynało od technicznego `HKCU`/`0 → 1`. W tej iteracji głównym tekstem
   jest skutek opisany zrozumiale, a wartości techniczne są drugorzędne.
3. **Potwierdzony problem pomocy:** pomoc mówiła o „500 jako celu”, chociaż
   chodziło o 500 odczytów zależnych od ADMX i cel 600 różnych zmian. Tekst
   poprawiono.
4. **Domknięto w kodzie:** Registry Manager zapisuje kopie w zarządzanym katalogu
   i pokazuje listę ostatnich zmian z przyciskiem cofnięcia. Audyt odróżnia
   nieustawioną wartość od odmowy dostępu i błędu. Nie sprawdzono jeszcze
   rzeczywistego zapisu i cofania na Windows.
5. **Domknięto w kodzie:** Repair Report domyślnie oznacza naprawę jako
   niepotwierdzoną w HTML, TXT, JSON i PDF. Potwierdzenie wymaga jawnego wyboru
   oraz opisu testu końcowego; prawdziwość wpisanego opisu nadal ocenia technik.

## Kandydaci do wspólnego wyboru

**P0 — przed kolejnymi ryzykownymi zmianami:** zarządzane kopie i lista
ostatnich działań z przyciskiem „cofnij”; jednoznaczne oznaczenie „odczyt / plan /
zmiana”; prosty ekran końcowy; rozróżnienie „nieustawione / odmowa dostępu /
błąd”; zakaz sugerowania usunięcia pliku na podstawie samej heurystyki.

**P1 — po P0:** aktywny adapter sieciowy jako domyślny wybór, kreator źródło–cel
dla obrazu dysku, tryb „sprawdź bez naprawy” w System Center, wskazówki dla
ADB/Termux, oznaczenie niepotwierdzonej diagnozy w PDF.

**P2 — wygoda:** większy tekst i tryb uproszczony, odczytywane na głos
wyjaśnienia, drukowana instrukcja dla serwisanta, szablony typowych problemów.

P0: zarządzane kopie i rozróżnienie statusów odczytu są wdrożone w kodzie.
P1: oznaczenie weryfikacji naprawy w raporcie jest wdrożone w kodzie.
Pozostałe pozycje są propozycjami, **nie funkcjami ukończonymi**. Rzeczywisty test
użyteczności powinien objąć kilka osób, polski Windows przy powiększeniu
125–200%, nawigację klawiaturą oraz przypadki odmowy UAC/braku Internetu.
