"""Assemble preview 0.3.2 with two rebuilt tools and unchanged verified 0.3.1 tools."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import shutil
import zipfile
from build_desktop import ROOT,build

VERSION='0.3.2'
changed={'prestige-backup','prestige-integrity-monitor'}
previous=json.loads((ROOT/'development/desktop-build.json').read_text(encoding='utf-8'))
assert previous['version']=='0.3.1' and len(previous['results'])==26
directory=ROOT/'dist'/('desktop-'+VERSION);directory.mkdir(exist_ok=True)
results=[]
for row in previous['results']:
    if row['project'] in changed:continue
    source=ROOT/'dist/desktop-0.3.1'/(row['project']+'.exe')
    with source.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']
    output=directory/source.name;shutil.copy2(source,output)
    results.append({**row,'executable':str(output),'tool_version':'0.3.1','reused_verified_binary':True})
with ThreadPoolExecutor(max_workers=2) as executor:
    for row in executor.map(lambda name:build(ROOT/name,VERSION,True),sorted(changed)):
        results.append({**row,'tool_version':VERSION});print(row['project']+': rebuilt and tested',flush=True)
results.sort(key=lambda row:row['project'])
(ROOT/'development/desktop-build.json').write_text(json.dumps({'version':VERSION,'results':results},indent=2),encoding='utf-8')
for name in ('LICENSE','THIRD_PARTY_NOTICES.txt','FONT-LICENSE.txt','START.txt'):
    shutil.copy2(ROOT/'dist/desktop-0.3.1'/name,directory/name)
(directory/'STATUS-WYDANIA.txt').write_text('''PRESTIGE TECH — zestaw testowy 0.3.2

Backup i Integrity Monitor: 0.3.2. Pozostałe 24 programy: niezmienione EXE 0.3.1.
Backup oznacza powodzenie dopiero po zakończeniu eksportów i ACL.
Restore zapisuje dziennik COMPLETE / FAILED / IN_PROGRESS obok katalogu docelowego.
Integrity Monitor nie uznaje nieodczytanych ACL/ADS za poprawną weryfikację.

Uruchom prestige-tech-dashboard.exe. Każdy EXE jest również samodzielny.
Źródła oraz instrukcje odzyskiwania znajdują się w osobnej paczce źródeł 0.3.2.
Testy administracyjne/sprzętowe, uruchomienie CI i poprawna odpowiedź API
(ostatnio HTTP 429) pozostają do wykonania w docelowym środowisku.
''',encoding='utf-8')
(directory/'SHA256SUMS.txt').write_text(''.join(row['sha256']+'  '+row['project']+'.exe\n' for row in results),encoding='utf-8')
archive=ROOT/'dist'/('prestige-tech-desktop-'+VERSION+'-windows-x64.zip')
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(directory.iterdir()):
        if path.is_file():bundle.write(path,path.name)
print(str(archive),flush=True)
