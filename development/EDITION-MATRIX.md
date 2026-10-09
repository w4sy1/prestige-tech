# Prestige Tech — zakres FREE i PRO (projekt, 2026-10-08)

Wybrane przez właściciela: FREE = diagnostyka i podstawowe naprawy;
PRO = pozostałe funkcje, aktywowane podpisanym kluczem offline.
Ta tabela jest kontraktem produktu, **nie potwierdzeniem wdrożenia bramek**
we wszystkich Centrach. Obecna licencja źródła nadal wymaga dostosowania
przed płatną dystrybucją.

| Centrum | FREE | PRO |
|---|---|---|
| Network | Odczyt adapterów/DNS, ping, DNS test, podstawowy LAN, plan i jawne flush DNS/DHCP renew | Zmiany DNS/MTU, zaawansowane Nmap/analiza ruchu, Sentinel/Firewall, harmonogram i eksport rozszerzony |
| Monitor | Hash pliku, jednorazowa kontrola folderu, odczyt historii | Ciągła obserwacja, profile, ACL/ADS, podpisy manifestów i zaawansowane porównania |
| Registry | Odczyt/audyt, 3 podstawowe ustawienia HKCU z kopią | Pozostałe zmiany, eksport różnic i przyszły katalog średniozaawansowany/zaawansowany |
| Storage | Inwentaryzacja dysków/USB i plan operacji | Obraz RAW, zmiana read-only USB, Backup/VSS/ACL, odtwarzanie i wersjonowanie PrestigeUSB |
| Android | Podstawowy odczyt ADB i listy aplikacji | Głębsza analiza uprawnień/AppOps, historia i porównania |
| Security | Podstawowy odczyt stanu ochrony i hash pliku | Triage, skan plików, korelacje, porównania i pakiet dowodowy |
| System | Migawka, podstawowa diagnostyka i plan naprawy; podstawowe naprawy sieci | SFC/DISM, czyszczenie z kwarantanną, eksporty i zaawansowane porównania |
| Termux | Odczyt stanu i plan | Instalacja, zmiany konfiguracji, backup i rollback |
| AI/iDiagnostics | Lokalna interpretacja pojedynczego raportu | Łączenie raportów, zewnętrzne AI i plan wieloetapowy |
| Report | Podstawowy HTML/JSON | PDF, historia spraw i rozszerzone szablony |
| Distant | Lokalny podgląd diagnostyki przed zgodą | Sesja zdalna, udostępnienie wyników i dziennik działań |

Zasady wdrożenia: bramka w GUI **i** w wywołaniu operacji; odczyt planu
i cofnięcie wcześniej wykonanej zmiany nie mogą być blokowane po wygaśnięciu
PRO. Licencja offline ma ważność, identyfikator i podpis Ed25519.
Klucz prywatny pozostaje poza repozytorium i EXE. Brak klucza lub błędny
podpis oznacza FREE. Przed wydaniem trzeba sprawdzić wygaśnięcie podczas
sesji, zmianę pliku licencji, instalację na czystym Windows i warunki licencji.
