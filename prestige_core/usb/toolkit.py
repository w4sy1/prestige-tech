from pathlib import Path
import re
import shutil
import sys
from .update import update,rollback
from prestige_core.backup.runtime import atomic_json,digest,entry,files,inside,parser,read_json

FOLDERS=['Diagnostics','Windows','Network','Android','Backup','Recovery','Reports','Tools']
EXCLUDE={'.git','.env','logs','reports','__pycache__','.venv','node_modules'}

def prepare(destination,tools):
    root=Path(destination).resolve()/'PrestigeUSB';sources=[Path(p).resolve() for p in tools]
    for source in sources:
        if not source.name.startswith('prestige-') or not source.is_dir():raise ValueError('Wskaż katalog narzędzia Prestige.')
        if root.is_relative_to(source):raise ValueError('Docelowy katalog znajduje się w źródle.')
        meta=read_json(source/'metadata.json')
        if not re.fullmatch(r'\d+\.\d+\.\d+',meta.get('version','')):raise ValueError('Brak poprawnej wersji.')
    if len({s.name for s in sources})!=len(sources):raise ValueError('Powtórzona nazwa narzędzia.')
    root.mkdir(parents=True,exist_ok=False)
    for folder in FOLDERS:(root/folder).mkdir()
    versions={}
    for source in sources:
        versions[source.name]=read_json(source/'metadata.json')['version']
        for path in files(source):
            relative=path.relative_to(source)
            if any(p in EXCLUDE or p.startswith('.env.') for p in relative.parts):continue
            target=inside(root,Path('Tools')/source.name/relative);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        for folder in ('logs','reports'):(root/'Tools'/source.name/folder).mkdir(exist_ok=True)
    manifest={'schema_version':1,'versions':versions,'files':{p.relative_to(root).as_posix():digest(p) for p in files(root)}}
    atomic_json(root/'manifest.json',manifest)
    return {'root':str(root),'files':len(manifest['files']),'versions':versions}

def verify(root):
    root=Path(root).resolve();data=read_json(root/'manifest.json')
    if data.get('schema_version')!=1 or not isinstance(data.get('files'),dict):raise ValueError('Błędny manifest.')
    missing=[];changed=[]
    for relative,expected in data['files'].items():
        path=inside(root,relative)
        if not path.is_file():missing.append(relative)
        elif digest(path)!=expected:changed.append(relative)
    actual={p.relative_to(root).as_posix() for p in files(root)}-{'manifest.json'}
    def user_data(relative):
        parts=Path(relative).parts
        return parts[0] in ('Reports','Backup') or (len(parts)>2 and parts[0]=='Tools' and parts[2] in ('logs','reports','__pycache__'))
    new=sorted(relative for relative in actual-set(data['files']) if not user_data(relative))
    return {'missing':missing,'changed':changed,'new':new,'versions':data.get('versions',{}),'ok':not(missing or changed or new)}

def build():
    p=parser('Tworzenie katalogu PrestigeUSB. Nigdy nie formatuje nośnika.')
    p.add_argument('command',nargs='?',choices=['prepare','verify','update','rollback']);p.add_argument('--destination');p.add_argument('--tool',action='append',default=[]);p.add_argument('--apply',action='store_true')
    return p

def handle(a):
    if not a.destination:raise ValueError('Podaj destination.')
    if a.command=='verify':return verify(a.destination)
    if a.command=='update':return update(a.destination,a.tool,prepare,a.apply)
    if a.command=='rollback':return rollback(a.destination,a.apply)
    if a.command=='prepare':
        if not a.apply:return {'plan':{'destination':str(Path(a.destination)/'PrestigeUSB'),'folders':FOLDERS,'tools':a.tool}}
        return prepare(a.destination,a.tool)
    raise ValueError('Wybierz polecenie.')

if __name__=='__main__':sys.exit(entry(build,handle))
