# Pomoc w codziennych problemach — projekt funkcji Prestige Tech

Stan: 2026-10-09. Dokument projektowy; opis nie oznacza gotowej implementacji.

## Główna obietnica

Użytkownik nie musi znać nazw usług, protokołów ani poleceń. Wybiera problem
zrozumiałym zdaniem, widzi co program sprawdził, co rzeczywiście naprawił,
co wymaga jego decyzji i jak wrócić do poprzedniego stanu. Zielony status
oznacza tylko elementy faktycznie sprawdzone; brak danych to żółty, nigdy zielony.

## Ekran główny

Trzy duże informacje: „Internet”, „Komputer”, „Bezpieczeństwo”. Pod nimi
przycisk „Coś nie działa”, „Przywróć moje pliki” i „Wezwij pomoc”. Każda karta
ma ostatni pomiar i źródło danych, bez wymyślonych procentów zdrowia.
Tryb dużych elementów: większa czcionka, wyraźny fokus klawiatury, mało
tekstu naraz, czytelne kontrasty, odczyt treści przez systemowy czytnik.

## 1. Automatyczne sprawdzanie komputera

- Harmonogram lokalny: po zalogowaniu lub o wybranej godzinie. Jeśli komputer
  był wyłączony, test wykonuje się przy następnym uruchomieniu. Nie budzi go
  sam i nie przerywa aktywnej pracy.
- Mikrotesty: internet i DNS, wolne miejsce, usługa drukowania, kopia zapasowa,
  aktualizacje, stan ochrony, ostatnie błędy. Każdy test ma limit czasu.
- Działania automatyczne tylko po włączeniu przez użytkownika osobnej reguły.
  Reguła obejmuje dokładnie jeden problem, warunki wykonania, limit prób,
  kontrolę wyniku i sposób przerwania. Domyślnie działa tylko diagnoza.
- Przykład: jeśli DNS przestaje rozwiązywać adresy, a router odpowiada,
  program może zaproponować czyszczenie pamięci DNS. Po wykonaniu ponawia
  test i dopiero wtedy pokazuje „Połączenie znów działa”. Jeśli kontrola
  nie przejdzie, pokazuje „Próba nie pomogła” i kolejny bezpieczny krok.
- Restart usługi drukowania, karty sieciowej czy procesów może przerwać pracę
  lub utracić niezapisane dane; nie jest domyślną naprawą nocną.
- Dziennik: wykryto → zaplanowano → potwierdzono → wykonano → sprawdzono.
  Powiadomienie zawiera jedną prostą informację i przycisk „Szczegóły”.

## 2. Pomoc z konkretnym problemem

Duże kafle: „Internet działa wolno”, „Nie ma dźwięku”, „Drukarka nie drukuje”,
„Brakuje miejsca”, „Komputer się zacina”, „Nie mogę otworzyć strony”,
„Zniknął plik”, „Wyskakuje dziwny komunikat”. Każda ścieżka ma ten sam układ:
krótki opis → pomiary → rozpoznanie z poziomem pewności → plan → działanie
pojedynczym przyciskiem → ponowny pomiar → cofnięcie lub dalsza pomoc.

Internet: odróżnić awarię routera, DNS, Wi-Fi, dostawcy i jednej strony.
Nie resetować karty automatycznie na podstawie samego „wolno”. Dźwięk:
sprawdzić wyciszenie aplikacji, główne wyjście, podłączone słuchawki i usługę
audio; pokazać właściwy suwak. Miejsce: wyliczyć odzyskiwalne bajty; domyślnie
tylko pliki tymczasowe objęte istniejącym kontrolowanym czyszczeniem. Folder
„Pobrane”, kosz, pliki przeglądarki i dokumenty wymagają osobnego podglądu;
nie wolno zakładać, że instalator w „Pobrane” jest zbędny.

## 3. Sprawdzanie podejrzanych stron i wiadomości

- „Sprawdź wiadomość lub stronę”: użytkownik przekazuje link, nagłówki albo
  treść bez danych prywatnych; program ocenia domenę, podobieństwo nazwy,
  przekierowania, reputację i treść. Wynik: „Podejrzane — nie wpisuj hasła”,
  „Brak wystarczających danych” albo „Nie znaleziono oznak oszustwa”.
- Nie twierdzić „to na pewno bank-oszust”, jeśli nie ma mocnego dowodu. Sam
  ważny certyfikat nie potwierdza uczciwości strony.
- Dla stron otwieranych w przeglądarce potrzebne jest osobne rozszerzenie lub
  integracja z przeglądarką, z minimalnymi uprawnieniami i widocznym stanem.
  Sam Dashboard nie widzi automatycznie każdej strony ani e-maila.
- Fałszywe powiadomienia: wykrycie uprawnień witryn i prowadzenie użytkownika
  do ich cofnięcia; nie modyfikować po cichu profili przeglądarki.
- Historia ostrzeżeń przechowuje domyślnie domenę i powód, nie całą wiadomość.

## 4. Bezpieczne logowanie

„Pas bezpieczeństwa” ocenia lokalnie siłę nowego hasła i powtórzenia w
sejfie, bez wysyłania hasła do AI. Przyjazne wskazówki: „To hasło jest już
używane”, „Dodaj dłuższe hasło” i „Włącz drugi sposób potwierdzenia”.
Pierwsza wersja powinna wspierać systemowe menedżery, passkeys i Windows Hello.
Własny sejf, synchronizacja i autouzupełnianie to osobny produkt wymagający
audytu bezpieczeństwa, modelu odzyskiwania dostępu i ochrony przed utratą
klucza. Sam krótki PIN nie jest wystarczającą podstawą szyfrowania.

## 5. Domowa sieć

Network Center pokazuje nazwę sieci, rodzaj zabezpieczenia i zmianę routera.
Nie próbuje logować się do routera hasłem admin/admin: to byłoby ryzykowne
i może blokować konto. Zamiast tego wyświetla instrukcję zmiany hasła oraz
ostrzeżenie przy sieci otwartej lub słabo zabezpieczonej. Nowe urządzenie
oznacza „nieznane”, a nie automatycznie „intruz”.

## 6. Czytelny pulpit i ustawienia dostępności

„Porządek na pulpicie” zapisuje układ i wykrywa nowe duplikaty skrótów, ale
nie blokuje eksploratora ani przeciągania plików globalnie. Przywrócenie
układu wymaga podglądu. Duży kursor, skala, kontrast i filtr nocny są profilami
z podglądem oraz przyciskiem „Wróć do poprzedniego wyglądu”.
Pasek ulubionych skrótów jest edytowany przez użytkownika. Linki do banku
i wyników badań dodaje się z oficjalnych adresów; program ostrzega przed
podmianą adresu i nigdy nie zapisuje danych logowania w skrócie.

## 7. Kopie plików i chronione dokumenty

Kopie dokumentów i pulpitu: pierwsza pełna kopia, kolejne wersje przyrostowe,
kontrola sum, limity miejsca, podgląd wersji i przywrócenie do nowej lokalizacji
przed nadpisaniem pliku. Komunikat „Kopia gotowa” dopiero po sprawdzeniu jej
odczytu. Kopia na tym samym dysku nie chroni przed awarią dysku; Dashboard
pokazuje ten fakt i proponuje nośnik zewnętrzny.
Chronione dokumenty to oddzielna funkcja z szyfrowaniem, odzyskiwaniem dostępu i jasną
zgodą na synchronizację. Dokumenty medyczne i umowy nie są domyślnie wysyłane
do AI, opiekuna ani chmury. Najpierw lokalny wariant i audyt bezpieczeństwa.

## 8. Zdalna pomoc i raport dla bliskiej osoby

SOS przygotowuje opis problemu i jednorazowy kod sesji. Użytkownik widzi,
komu i jakie dane wysyła. Zrzut ekranu jest opcjonalny z podglądem i ukryciem
wrażliwych okien. Zdalny dostęp wymaga bieżącej zgody, pokazuje aktywną sesję,
ma natychmiastowe „Zakończ” i dziennik czynności. Bez stałego ukrytego dostępu.
Raport dla opiekuna jest opt-in i zawiera tylko wybrane statusy. Kanał wysyłki
i tożsamość opiekuna trzeba zweryfikować przed uruchomieniem. Nie wysyłać
historii przeglądania, plików ani haseł.

## Wspólna architektura

Dashboard: kafle, trzy kolory, historia i prosty język. Centra: wykonują
konkretne pomiary i operacje. Widok pomocy składa wyniki w plan. Silnik zasad
decyduje, czy dana operacja może być automatyczna; każda ma identyfikator,
warunki, limit, dziennik, test końcowy i klasę ryzyka. Report Center zbiera
wyniki bez nadpisywania faktów przez AI. AI objaśnia dane i podaje źródła,
ale nie samodzielnie zatwierdza naprawy ani nie diagnozuje oszustwa z pewnością.

## Kolejność budowy

1. Kafelki problemów, plany i uczciwe trzy stany; wyłącznie odczyt.
2. Powiązanie z istniejącymi Network/System/Storage/Report i weryfikacja wyniku.
3. Opcjonalne, pojedyncze reguły automatyczne z limitem prób i dziennikiem.
4. Kopie i przywracanie, potem dostępność i ochrona przed oszustwami.
5. SOS, chronione dokumenty i menedżer haseł dopiero po osobnym projekcie bezpieczeństwa i testach.

## Włączenie do istniejących modułów

| Nazwa dla użytkownika | Moduł | Test akceptacyjny | Stan |
|---|---|---|---|
| Pomoc z Internetem | Network Center | Pomiar rozróżnia router, DNS i Internet; po planie wynik jest zmierzony ponownie | Częściowo: istnieje prowadzony pomiar i plan |
| Znane urządzenia | Network Center / Sentinel | Użytkownik oznacza urządzenie; ponowny odczyt zachowuje oznaczenie | Częściowo: istnieje lokalny rejestr zaufania |
| Sprawdzenie komputera | System Center / Dashboard | Harmonogram wykonuje tylko odczyt, zapisuje pominięty test i przyczynę | Częściowo: jednorazowy przegląd i zapis JSON; harmonogram do zrobienia |
| Pomoc z dźwiękiem | System Center | Pokazuje rzeczywiste wyciszenie i wyjście audio; nie zmienia ustawień bez potwierdzenia | Częściowo: odczyt urządzeń; wyciszenie i wyjście pozostają UNKNOWN |
| Pomoc z drukarką | System Center | Odczytuje usługę i kolejkę; po ewentualnym restarcie sprawdza stan ponownie | Częściowo: odczyt usługi, drukarek i liczby zadań; naprawa do zrobienia |
| Zwolnij miejsce | System Center / Storage & Recovery | Lista pokazuje ścieżki i bajty, nie obejmuje Dokumentów ani Pobranych bez wyboru | Częściowo: istnieje analiza i kontrolowane czyszczenie |
| Sprawdź podejrzany link | Security Center / AI Center | Wynik podaje domenę, dowody, niepewność i nie wysyła treści bez zgody | Częściowo: lokalna analiza adresu; bez treści strony i reputacji |
| Powiadomienia ze stron | Security Center | Pokazuje uprawnienia witryn i prowadzi do ich wyłączenia w przeglądarce | Częściowo: lokalny odczyt Chrome/Edge; zmiana uprawnień w przeglądarce do zrobienia |
| Bezpieczne logowanie | Security Center | Hasła nie trafiają do logów ani AI; można sprawdzić powtórzenia lokalnie | Do zrobienia; własny sejf wymaga audytu |
| Bezpieczeństwo Wi-Fi | Network Center / Sentinel | Otwarta sieć daje ostrzeżenie; nieznany host nie jest nazywany intruzem | Częściowo: odczyt szyfrowania bieżącego Wi-Fi; hasła routera nie sprawdzono |
| Czytelny ekran | Dashboard / System Center | Każdą zmianę skali i kontrastu można cofnąć | Do zrobienia |
| Skróty do ważnych stron | Dashboard | Użytkownik widzi pełny adres i może usunąć skrót | Do zrobienia |
| Kopie moich plików | Storage & Recovery / Monitor | Odtworzenie jest sprawdzone bez nadpisania oryginału | Częściowo: istnieją kopie i wersjonowanie |
| Chronione dokumenty | Storage & Recovery / Security Center | Dane nie opuszczają komputera bez zgody; dostęp da się odzyskać | Do zrobienia |
| Wezwij pomoc | Distant / Report Center | Zrzut jest opcjonalny; sesja ma zgodę, kod jednorazowy i natychmiastowe zakończenie | Do zrobienia |
| Raport dla bliskiej osoby | Report Center | Zakres danych i odbiorca są zatwierdzone; raport nie zawiera haseł | Częściowo: lokalny podgląd i zapis; brak wysyłki na telefon |

„Do zrobienia” oznacza brak gotowej funkcji. Test akceptacyjny opisuje warunek
ukończenia, a nie test już wykonany. Zanim nowa funkcja trafi na ekran główny,
musi mieć rzeczywiste źródło danych, obsługę błędów i wynik zrozumiały dla
użytkownika.
