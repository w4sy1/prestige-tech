"""Record the four rollback fixes without changing other project versions."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[1]
changes={
 'prestige-pc-cleanup':('ROLLBACK','Odmowa przy brakujących plikach kwarantanny; wyłączne tworzenie pliku docelowego bez nadpisywania.'),
 'prestige-usb-toolkit':('ROLLBACK','Weryfikacja poprzedniej wersji przed rollbackiem; odmowa dla brakującej, zmienionej lub rozszerzonej kopii.'),
 'prestige-termux-setup':('RECOVERY','Atomowe zapisy konfiguracji i odtwarzania, także przy przerwaniu konfiguracji wielu plików.'),
 'prestige-network-optimizer':('RECOVERY','Rollback nie powtarza przywróconych ustawień ani nie nadpisuje późniejszego trybu automatycznego DNS.')}
for name,(guide,description) in changes.items():
    project=ROOT/name;version=json.loads((project/'metadata.json').read_text())['version']
    readme=project/'README.md';text=readme.read_text(encoding='utf-8')
    text=re.sub(r'(?m)^(PRESTIGE TECH[^\n]*?v)\d+\.\d+\.\d+',lambda match:match[1]+version,text)
    marker='## Poprawki rollbacku '+version
    if marker not in text:text+='\n'+marker+'\n\n'+description+'\n\nSzczegóły: [docs/'+guide+'.md](docs/'+guide+'.md).\n'
    readme.write_text(text,encoding='utf-8')
    changelog=project/'CHANGELOG.md';text=changelog.read_text(encoding='utf-8')
    if '## '+version not in text:text+='\n## '+version+'\n\n- '+description+'\n- Testy błędów i zachowania danych.\n'
    changelog.write_text(text,encoding='utf-8')
