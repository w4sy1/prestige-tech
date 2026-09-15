"""Build selected changed tools, preserving verified binaries of other tools."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from build_desktop import ROOT,build

parser=argparse.ArgumentParser()
parser.add_argument('--version',required=True);parser.add_argument('--previous',required=True)
parser.add_argument('--project',action='append',required=True)
args=parser.parse_args()
if not all(re.fullmatch(r'\d+\.\d+\.\d+',value) for value in (args.version,args.previous)):raise ValueError('Expected X.Y.Z versions')
previous=json.loads((ROOT/'development/desktop-build.json').read_text(encoding='utf-8'))
assert previous['version']==args.previous and len(previous['results'])==26
changed=set(args.project);assert changed<={row['project'] for row in previous['results']}
directory=ROOT/'dist'/('desktop-'+args.version);directory.mkdir(exist_ok=True)
archive=ROOT/'dist'/('prestige-tech-desktop-'+args.version+'-windows-x64.zip')
if archive.exists():raise FileExistsError(archive)
results=[]
for row in previous['results']:
    if row['project'] in changed:continue
    source=ROOT/'dist'/('desktop-'+args.previous)/(row['project']+'.exe')
    with source.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']
    output=directory/source.name;shutil.copy2(source,output)
    results.append({**row,'executable':str(output),'reused_verified_binary':True})
with ThreadPoolExecutor(max_workers=2) as executor:
    for row in executor.map(lambda name:build(ROOT/name,args.version,True),sorted(changed)):
        version=json.loads((ROOT/row['project']/'metadata.json').read_text())['version']
        results.append({**row,'tool_version':version});print(row['project']+': rebuilt and tested',flush=True)
results.sort(key=lambda row:row['project'])
(ROOT/'development/desktop-build.json').write_text(json.dumps({'version':args.version,'results':results},indent=2),encoding='utf-8')
for name in ('LICENSE','THIRD_PARTY_NOTICES.txt','FONT-LICENSE.txt','START.txt'):
    shutil.copy2(ROOT/'dist'/('desktop-'+args.previous)/name,directory/name)
(directory/'STATUS-WYDANIA.txt').write_text('PRESTIGE TECH — zestaw testowy '+args.version+'\n\nZaktualizowano: '+', '.join(sorted(changed))+'.\nPozostałe pliki EXE są niezmienione względem paczki '+args.previous+'.\n\nWersje programów:\n'+''.join(row['project']+': '+row.get('tool_version',args.previous)+'\n' for row in results)+'\nTesty sprzętowe i administracyjne wymagają docelowego środowiska. Ostatnie API: HTTP 429.\n',encoding='utf-8')
(directory/'SHA256SUMS.txt').write_text(''.join(row['sha256']+'  '+row['project']+'.exe\n' for row in results),encoding='utf-8')
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(directory.iterdir()):
        if path.is_file():bundle.write(path,path.name)
print(str(archive),flush=True)
