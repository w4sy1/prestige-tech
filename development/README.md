# Weryfikacja i dystrybucja

Polecenia wykonuj z katalogu głównego zestawu:

```powershell
python development/verify.py
python -m pip wheel ./prestige-tech-cli --no-deps --wheel-dir ./prestige-tech-cli/reports/wheels
python development/smoke.py
```

verify.py uruchamia każdy projekt w osobnym procesie, sprawdza strukturę i MIT.
smoke.py wymaga najpierw zbudowanego wheel. Instaluje go do tymczasowego venv,
sprawdza routing CLI i operacje na syntetycznych danych; nie wysyła ruchu do Internetu.
Budowa wheel może pobrać izolowane zależności budowania (setuptools).

checkpoint.py zapisuje commity lokalnych repozytoriów po przejściu testów.
Nie publikuje kodu i nie zmienia globalnej konfiguracji Git.
package_release.py tworzy nowy ZIP z zatwierdzonych plików i weryfikuje jego integralność.
Wymaga repozytoriów Git, więc służy do pracy w oryginalnym workspace, nie w rozpakowanym ZIP.

standalone.py tworzy tylko jeden wskazany projekt. runtime_template.py nie jest wspólną
zależnością wykonawczą; update_runtime.py kopiuje go do samodzielnych projektów.
Po każdej zmianie runtime uruchom wszystkie testy ponownie.
