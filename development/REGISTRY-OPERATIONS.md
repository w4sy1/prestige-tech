# Registry Manager — licznik operacji (2026-09-28)

Aktualizacja 2026-10-08: katalog zmian HKCU ma teraz 20 pozycji, po dodaniu
ShowSuperHidden, ShowTypeOverlay, czterech polityk HKCU, ShowStatusBar oraz
trzech ustawień motywu/przezroczystości i koloru pasków tytułu.
GUI opisuje ich skutki prostym językiem,
oznacza poziom i FREE/PRO. Kod weryfikuje podpisany klucz PRO offline, ale
publiczny klucz wydawcy i warunki płatnego wydania nie są jeszcze gotowe.
Użytkownik potwierdził cel 200/200/200 zmian. Nadal pozostaje 580 operacji
do indywidualnego opracowania i testów. Nowe 012/013 mają kopię także dla
nieistniejącej wartości, warunkowe cofnięcie oraz odmowę na niewspieranej edycji.
Sprawdzono je na fixture, bez rzeczywistego zapisu na Windows.
Polityki REG-WRITE-012–015 są według dokumentacji Microsoft wspierane w
Windows Pro/Enterprise/Education; na tym komputerze plan bez trybu
eksperymentalnego odmówił z powodu innej edycji. Na życzenie użytkownika
tryb eksperymentalny pozwala wykonać plan/zapis mimo braku oficjalnego
wsparcia, ale pozostaje domyślnie wyłączony i nie stanowi potwierdzenia efektu.
REG-WRITE-016–020 mają poprawny lokalny odczyt DWORD; nie wykonywano
rzeczywistego zapisu i cofnięcia.

Aktualny katalog na tym komputerze: **500 odrębnych odczytów** — 29 ręcznie
opisanych niżej oraz 471 wyprowadzonych z 33 lokalnych szablonów Microsoft
`C:\Windows\PolicyDefinitions\*.admx`. Parser przyjmuje tylko bezpośrednio
określoną nazwę wartości i klasę User/Machine/Both, usuwa duplikaty po
gałęzi/kluczu/nazwie i nie odczytuje danych innych niż wskazane wartości.
Wszystkie 500 wywołań odczytu na bieżącym Windows zakończyło się bez błędu
wykonania: 66 wartości dostępnych, 434 zasad nieustawionych lub kluczy
nieistniejących. Treści wartości nie zapisano w raporcie. Liczba ADMX zależy
od instalacji Windows, więc na innym komputerze katalog może mieć inną
liczność. Nie jest to 500 operacji zmieniających rejestr ani potwierdzenie
obecności wszystkich zasad.
GUI ma odczyt pojedynczych pozycji i przerwalny audyt całego katalogu.
Audyt podaje liczniki/statusy i identyfikatory błędów bez treści wartości.

Zmiany: REG-WRITE-001 oraz REG-WRITE-002–009, czyli dziewięć wąskich ustawień
HKCU Explorer. Dla 002–009 dodano plan, nową kopię JSON ze stanem PREPARED,
weryfikację zapisu, próbę cofnięcia po błędzie i rollback odmówiony po zmianie
wartości przez inny proces. Wszystkie osiem nowych zmian przeszło fixture;
rzeczywistego zapisu/rollbacku Windows nie testowano zgodnie z odłożeniem
testów VM. Nie liczyć ich jako zweryfikowanych na żywym systemie.

Źródła katalogu: lokalne szablony ADMX Microsoftu oraz [oficjalna dokumentacja
ustawień Eksploratora](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca),
[UAC](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration)
i [wersji kompilacji Windows](https://learn.microsoft.com/en-us/intune/app-management/deployment/deploy-win32-update-package).

Poniższa tabela opisuje 29 ręcznie skatalogowanych odczytów. Pozostałe 471
ma źródło i identyfikator przypisane przez importer ADMX w czasie uruchomienia.

Stan ręcznego katalogu: **29 zaimplementowanych odczytów / 29 sprawdzonych na
fixture i przez lokalny odczyt Windows**. Wraz z ADMX: 500 odczytów na tym
komputerze. Pełny zakres zmian rejestru nadal nie jest ukończony.
Odczyt nie jest zmianą rejestru. Żadna operacja zapisu, backupu ani rollbacku
nie jest jeszcze liczona jako gotowa.

| ID | Działanie | Źródło | Fixture | Lokalny odczyt |
|---|---|---|---|---|
| REG-READ-001 | Odczyt siedmiu lokalizacji folderów osobistych HKCU | [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/change-personal-folder-location-fails) | PASS | PASS: 7 wpisów |
| REG-READ-002 | Odczyt wpisów autostartu HKCU Run | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys) | PASS | PASS: 8 wpisów |
| REG-READ-003 | Odczyt wpisów jednorazowego autostartu HKCU RunOnce | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys) | PASS | PASS: 0 wpisów |
| REG-READ-004 | Odczyt wpisów autostartu komputera HKLM Run (natywny widok) | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys) | PASS | PASS: 3 wpisy |
| REG-READ-005 | Odczyt wpisów jednorazowego autostartu komputera HKLM RunOnce (natywny widok) | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys) | PASS | PASS: 1 wpis |
| REG-READ-006 | Explorer: HideFileExt | [Microsoft Learn](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca) | PASS | PASS: wartość dostępna |
| REG-READ-007 | Explorer: Hidden | [Microsoft Learn](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca) | PASS | PASS: wartość dostępna |
| REG-READ-008 | Explorer: ShowSuperHidden | [Microsoft Learn](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca) | PASS | PASS: wartość dostępna |
| REG-READ-009 | Explorer: ShowTypeOverlay | [Microsoft Learn](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca) | PASS | PASS: wartość dostępna |
| REG-READ-010 | Explorer: SeparateProcess | [Microsoft Learn](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca) | PASS | PASS: wartość dostępna |
| REG-READ-011 | Explorer: ShowInfoTip | [Microsoft Learn](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca) | PASS | PASS: wartość dostępna |
| REG-READ-012 | Explorer: ShowCompColor | [Microsoft Learn](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca) | PASS | PASS: wartość dostępna |
| REG-READ-013 | UAC: EnableLUA | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-014 | UAC: ConsentPromptBehaviorAdmin | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-015 | UAC: ConsentPromptBehaviorUser | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-016 | UAC: EnableInstallerDetection | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-017 | UAC: ValidateAdminCodeSignatures | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-018 | UAC: EnableSecureUIAPaths | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-019 | UAC: PromptOnSecureDesktop | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-020 | UAC: EnableVirtualization | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-021 | UAC: EnableUIADesktopToggle | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-022 | ProxyEnable użytkownika | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/wininet/enabling-internet-functionality) | PASS | PASS: wartość dostępna |
| REG-READ-023 | RDP: fDenyTSConnections | [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-server/remote/remote-desktop-cannot-connect-remote-computer) | PASS | PASS: wartość dostępna |
| REG-READ-024 | System: DevicePath | [Microsoft Learn](https://learn.microsoft.com/en-us/powershell/scripting/samples/working-with-registry-entries) | PASS | PASS: wartość dostępna |
| REG-READ-025 | System: ProgramFilesDir | [Microsoft Learn](https://learn.microsoft.com/en-us/powershell/scripting/samples/working-with-registry-entries) | PASS | PASS: wartość dostępna |
| REG-READ-026 | UAC: FilterAdministratorToken | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-027 | UAC: InteractiveLogonFirst | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration) | PASS | PASS: wartość dostępna |
| REG-READ-028 | System: CurrentBuildNumber | [Microsoft Learn](https://learn.microsoft.com/en-us/intune/app-management/deployment/deploy-win32-update-package) | PASS | PASS: wartość dostępna |
| REG-READ-029 | System: UBR | [Microsoft Learn](https://learn.microsoft.com/en-us/intune/app-management/deployment/deploy-win32-update-package) | PASS | PASS: wartość dostępna |

Liczby wpisów opisują wyłącznie stan testowanego komputera w chwili odczytu;
nie są zawartością opublikowanego raportu. Wartości rejestru nie trafiły do
testów ani tego dokumentu. Brak wpisów w RunOnce nie oznacza błędu.

Nowe operacje 006–025 odczytują pojedyncze, odrębne wartości konfiguracji.
Fixture sprawdza osobno każdy wpis, a lokalny odczyt potwierdził obecność
wszystkich 29 ręcznych operacji bez zapisu wartości do raportu. To nie dowodzi obecności
tych wartości na innych wersjach Windows; brak jest oznaczany Niedostępne.

Następny etap: parytet pozostałych funkcji starego Registry Tool, testy zapisów
i rollbacku w VM oraz automatyczny audyt pokrycia zasad ADMX na innych Windows.

## REG-WRITE-001 — pokaż rozszerzenia plików (fixture, bez testu zapisu Windows)

HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\HideFileExt: REG_DWORD 1 → 0. GUI wymaga potwierdzenia i nowego pliku kopii JSON; zapis jest weryfikowany, a cofnięcie przywraca 1 tylko gdy bieżąca wartość nadal wynosi 0. Test fixture PASS, lokalny odczyt typu PASS; rzeczywisty zapis/rollback na VM NIE TESTOWANY. Nie zaliczono do 25 operacji zweryfikowanych na żywym Windows. Źródło: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/3c837e92-016e-4148-86e5-b4f0381a757f
