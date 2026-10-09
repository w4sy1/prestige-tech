# Registry Manager — audyt pomysłów na zmiany systemu

Stan: 2026-10-08. Ten dokument jest kolejką weryfikacyjną, **nie katalogiem gotowych przycisków**.
Ręcznie zatwierdzonych zmian w aplikacji jest 20. Polityki
`REG-WRITE-012–015`, ustawienie Eksploratora `REG-WRITE-016` i trzy ustawienia
wyglądu `REG-WRITE-017–020` przeszły fixture,
bez rzeczywistego zapisu Windows. Każda następna zmiana wymaga
opisu dla nietechnicznej osoby, źródła Microsoft, zakresu wersji i edycji Windows,
planu, kopii zastanego stanu (także gdy wartość nie istniała), kontroli po zapisie,
cofnięcia i testu zachowania na odpowiedniej wersji systemu. Odczyt ADMX nie jest
automatycznym upoważnieniem do zapisu dowolnej polityki.

## Audyt artykułu Hetman Recovery

Źródło pomysłów: https://hetmanrecovery.com/pl/blog/windows-11-registry-edits-to-improve-system-performance.htm

| Pomysł | Co faktycznie zmienia | Decyzja dla katalogu |
|---|---|---|
| Punkt przywracania | Zabezpieczenie przed zmianą, nie tweak wydajności | Wymóg procesu dla operacji wysokiego ryzyka; nie liczyć jako operacji rejestru |
| Klasyczne menu kontekstowe | Wygląd i liczba kliknięć | Kandydat wygody; wymaga potwierdzenia wspierania w aktualnym Windows 11 |
| `DisableSearchBoxSuggestions` | Według Microsoft blokuje historię podpowiedzi w polu wyszukiwania **Eksploratora plików** | Dodane jako REG-WRITE-012; nie opisywać jako wyłączenie wyników Bing w Start |
| Własna pozycja menu kontekstowego | Skrót uruchamiający program | Kandydat zaawansowany; wymaga walidacji bezpiecznej ścieżki, cytowania i usuwania tylko własnego wpisu |
| `NoAutoUpdate` | Wyłączenie automatycznych aktualizacji | Nie dodawać jako „optymalizacja”; utrudnia dostarczanie poprawek bezpieczeństwa |
| Ukrycie OneDrive w Eksploratorze | Zmiana widoku panelu | Kandydat wygody tylko po sprawdzeniu obsługi w bieżącym Windows; nie usuwa programu ani danych |
| `NoLockScreen` | Pomija dodatkowy ekran przed logowaniem | Kandydat wygody dla wspieranych edycji Windows; nie wyłącza ekranu logowania ani hasła |
| `DisableNotificationCenter` | Usuwa centrum zadań/powiadomień z paska | Dodane jako REG-WRITE-013 z ostrzeżeniem o przeoczonych powiadomieniach; wymaga restartu |

Microsoft opisuje `DisableSearchBoxSuggestions` jako politykę Eksploratora, nie
przełącznik wyszukiwarki Bing:
https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-windowsexplorer#disablesearchboxsuggestions

Microsoft określa zakres wersji/edycji dla `NoLockScreen`:
https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-controlpaneldisplay#cpl_personalization_nolockscreen

Microsoft opisuje efekt i restart dla `DisableNotificationCenter`:
https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-taskbar#disablenotificationcenter

W kolejnej partii dodano `HideContentViewModeSnippets` (REG-WRITE-014),
`DisableThumbsDBOnNetworkFolders` (REG-WRITE-015) oraz `ShowStatusBar`
(REG-WRITE-016). Pierwsze dwie to polityki z udokumentowanym zakresem edycji
Pro/Enterprise/Education. `ShowStatusBar` jest ustawieniem HKCU Eksploratora;
typ DWORD i obecność wartości potwierdzono tylko odczytem na bieżącym komputerze.
Źródła Microsoft:
https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-windowsexplorer#hidecontentviewmodesnippets
https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-thumbnails#disablethumbsdbonnetworkfolders
https://learn.microsoft.com/en-us/windows/apps/develop/settings/settings-common

Test regresyjny wykrył i zabezpieczył wyścig przed zapisem polityki: jeśli
inny proces zmieni wartość po utworzeniu kopii, transakcja nie przywraca jej
samowolnie, tylko kończy rekord statusem `ABORTED_CONFLICT`.

Użytkownik wybrał tryb eksperymentalny na niewspieranych edycjach Windows.
GUI ma domyślnie wyłączony przełącznik sesyjny; plan wskazuje brak oficjalnego
wsparcia, a każde zastosowanie wymaga ostrzeżenia, nowej kopii i potwierdzenia.
Nie oznacza to faktycznego działania polityki na Windows Home. Cofnięcie jest
dostępne również po wyłączeniu trybu eksperymentalnego.

Ustawienia wyglądu `AppsUseLightTheme`, `SystemUsesLightTheme` i
`EnableTransparency` odpowiadają wartościom opisanym przez Microsoft w
https://learn.microsoft.com/en-us/windows/apps/develop/settings/settings-common .
Ich typ DWORD i obecność potwierdzono lokalnym odczytem bez zapisu.
To samo źródło opisuje `ColorPrevalence` w HKCU\Software\Microsoft\Windows\DWM;
dodano je jako REG-WRITE-020. Lokalny odczyt potwierdził obecność DWORD.

## Zasada liczenia

Jedno niezależne działanie użytkownika = jedna operacja. Stan włączony i wyłączony
tej samej polityki nie daje dwóch pozycji. Różne wartości tego samego klucza nie są
oddzielnymi funkcjami, jeśli nie mają osobnego, sensownego efektu. Odczyty, plan,
backup i cofnięcie są częściami jednej operacji. Kategorie tematyczne (wygoda,
wydajność, prywatność, sieć, bezpieczeństwo) nie zastępują poziomów trudności.

Użytkownik potwierdził cel 200 pozycji na każdy z trzech poziomów: 600 indywidualnych
operacji. Nie należy sztucznie zapełniać tej liczby poradami nieaktualnymi,
powtórzeniami lub zmianami osłabiającymi zabezpieczenia. Dla każdego kandydata
trzeba wskazać mierzalny/skonkretyzowany skutek, a dla „przyspieszania” osobny
scenariusz pomiaru; obietnica ogólnego wzrostu wydajności nie wystarcza.
