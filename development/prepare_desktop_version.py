"""Prepare consistent metadata for a tested desktop preview, without retagging releases."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.3.1'
for project in sorted(ROOT.glob('prestige-*')):
    metadata=project/'metadata.json'
    if not metadata.exists():continue
    record=json.loads(metadata.read_text(encoding='utf-8'));old=record['version'];record['version']=VERSION
    metadata.write_text(json.dumps(record,ensure_ascii=False)+'\n',encoding='utf-8')
    pyproject=project/'pyproject.toml'
    if pyproject.exists():
        text=pyproject.read_text(encoding='utf-8')
        text=re.sub(r'(?m)^version = "[^"]+"$',f'version = "{VERSION}"',text)
        pyproject.write_text(text,encoding='utf-8')
    script=project/'prestige.ps1'
    if script.exists():script.write_text(script.read_text(encoding='utf-8').replace(old,VERSION),encoding='utf-8')
    changelog=project/'CHANGELOG.md';text=changelog.read_text(encoding='utf-8')
    if '## '+VERSION not in text:
        text+='\n## '+VERSION+' — wydanie testowe desktop\n\n- GUI, PDF i samodzielny build EXE.\n- Ograniczony bufor wyników, poprawiona obsługa UTF-8 i zatrzymywania backendu.\n- Konfiguracja testów CI; zależności zachowują oryginalne licencje.\n'
        if project.name=='prestige-malware-triage':text+='- Pomiar GPU w czasie, korelacja PID i poprawiony okres pomiaru CPU.\n'
        changelog.write_text(text,encoding='utf-8')
    (project/'docs/DESKTOP-STATUS.md').write_text('''# Desktop 0.3.1 — wydanie testowe

GUI zachowuje ostatnie 65536 znaków wyniku. Po skróceniu informuje o tym
w pasku stanu. TXT i PDF zapisane z okna obejmują ten bufor; pełny raport
zapisz opcją wyjściową backendu. Długie wiersze przewijaj poziomo.
Przerwanie zatrzymuje uruchomiony proces i jego dzieci na Windows.
Po przerwaniu zapisu sprawdź dziennik oraz backup przed kolejną operacją.

Wersja zawiera lokalne testy automatyczne. Nie oznacza potwierdzenia operacji
administracyjnych, fizycznych urządzeń Android ani wszystkich sterowników.
Zewnętrzne AI wymaga własnego dostępnego konta API; ostatnia próba miała HTTP 429.
''',encoding='utf-8')
print('Prepared version '+VERSION+' for 26 projects.')
