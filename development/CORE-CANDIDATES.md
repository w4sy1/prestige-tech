# Kandydaci do przyszłego core

Po implementacji samodzielnych wersji widoczne są powtórzenia: runtime.py (raporty,
branding, JSONL, backendy), hashowanie/iterowanie plików, walidacja ścieżek i launcher.
Każde repo ma własną kopię małego runtime, żeby zachować samodzielne uruchamianie.
development/update_runtime.py synchronizuje kopie podczas rozwoju, nie jest zależnością
wykonawczą. Zmiana runtime wymaga testów wszystkich programów.

Przyszłe prestige-tech-core może wyodrębnić reports/branding/logging/config/models
z zachowaniem schema_version. Nie powinno zależeć od narzędzi. Najpierw potrzebne
są testy docelowych platform i stabilizacja kontraktów MVP.
