"""Align independent READMEs with desktop features and privacy behavior."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
for project in sorted(ROOT.glob('prestige-*')):
    path=project/'README.md'
    if not path.exists():continue
    text=path.read_text(encoding='utf-8')
    text=re.sub(r'(?m)^(PRESTIGE TECH[^\n]*?v)\d+\.\d+\.\d+',r'\g<1>0.3.1',text)
    text=text.replace('Bez instalowania pakietów pip.','Podstawowy CLI używa biblioteki standardowej. PDF wymaga requirements-gui.txt; podpisy, jeśli dostępne, wymagają requirements-signing.txt.')
    if '## GUI i EXE 0.3.1' not in text:
        text+='''
## GUI i EXE 0.3.1

Uruchom `python gui.py` albo samodzielny EXE. W EXE interpreter, PDF i potrzebne
biblioteki Python są dołączone. Zewnętrzne backendy systemowe pozostają wymagane.
Budowa: [docs/BUILD.md](docs/BUILD.md). Obsługa: [docs/GUI.md](docs/GUI.md).
Ograniczenia bufora i testów: [docs/DESKTOP-STATUS.md](docs/DESKTOP-STATUS.md).
Własny kod ma licencję MIT. Licencje zależności: THIRD_PARTY_NOTICES.txt.
'''
    if project.name=='prestige-ai-diagnostic-assistant':
        text=text.replace('Lokalna normalizacja raportów, reguły i scoring bez wysyłania danych oraz bez działań administracyjnych.',
            'Domyślnie lokalna normalizacja, reguły i scoring. Opcjonalny provider OpenAI wysyła wybrane metryki. Program nie wykonuje działań administracyjnych.')
        text=text.replace('Dane pozostają lokalne. Polecenia sieciowe wymagają świadomego wywołania;',
            'Dane pozostają lokalne w trybie local. Wybranie OpenAI oznacza wysłanie metryk; GUI pyta przed wysłaniem. Polecenia sieciowe wymagają świadomego wywołania;')
        if 'docs/EXTERNAL_AI.md' not in text:text+='\nKonfiguracja klucza i zakres wysyłki: [docs/EXTERNAL_AI.md](docs/EXTERNAL_AI.md).\n'
    path.write_text(text,encoding='utf-8')
print('Updated README documentation in 26 projects.')
