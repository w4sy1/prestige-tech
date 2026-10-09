from pathlib import Path
import os
import shutil
import tempfile
import time
import uuid
from .cleanup_runtime import atomic_json,digest,files,inside,read_json
from .security_check import _powershell

def temp_roots():
    roots=[Path(tempfile.gettempdir()).resolve()]
    if os.environ.get('WINDIR'):roots.append((Path(os.environ['WINDIR'])/'Temp').resolve())
    return roots

def profiles():
    result={'temp':str(Path(tempfile.gettempdir()).resolve())}
    if os.environ.get('WINDIR'):
        result['windows-temp']=str(Path(os.environ['WINDIR'])/'Temp')
        result['windows-logs']=str(Path(os.environ['WINDIR'])/'Logs')
    if os.environ.get('LOCALAPPDATA'):
        result['directx-cache']=str(Path(os.environ['LOCALAPPDATA'])/'D3DSCache')
        result['thumbnails']=str(Path(os.environ['LOCALAPPDATA'])/'Microsoft/Windows/Explorer')
    result['downloads']=str(Path.home()/'Downloads')
    if os.name=='nt':result['recycle-bin']='Kosz bieżącego użytkownika — analiza'
    return result

def scan_recycle():
    if os.name!='nt':raise ValueError('Odczyt kosza wymaga Windows.')
    rows=_powershell(r'''$shell=New-Object -ComObject Shell.Application;$bin=$shell.NameSpace(10)
if($null -eq $bin){throw 'Kosz niedostępny.'}
$rows=@(foreach($item in $bin.Items()){[pscustomobject]@{name=[string]$item.Name;size=[long]$item.Size;is_folder=[bool]$item.IsFolder;deleted=[string]$item.ExtendedProperty('System.Recycle.DateDeleted')}})
ConvertTo-Json -InputObject $rows -Depth 4''')
    return {'schema_version':1,'kind':'recycle-bin','analysis_only':True,'items':rows or [],
        'clean_allowed':False,'note':'Analiza kosza. Trwałe opróżnianie wymaga osobnego planu i jawnej zgody w Windows Toolkit; brak rollbacku.'}


def scan_usage(root, *, max_files=100000, top_limit=20):
    """Odczyt zajętości bez podążania za symlinkami; nigdy nie daje prawa do czyszczenia."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or not 1 <= max_files <= 1000000 or not 1 <= top_limit <= 100:
        raise ValueError('Nieprawidłowy katalog lub limit analizy.')
    stack = [root]
    count = total = 0
    visited_dirs = 0
    largest = []
    errors = 0
    while stack and count < max_files and visited_dirs < max_files:
        folder = stack.pop()
        visited_dirs += 1
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            size = entry.stat(follow_symlinks=False).st_size
                            count += 1
                            total += size
                            largest.append({'path':str(Path(entry.path).relative_to(root)), 'size':size})
                            largest.sort(key=lambda row:row['size'], reverse=True)
                            del largest[top_limit:]
                            if count >= max_files:
                                break
                    except OSError:
                        errors += 1
        except OSError:
            errors += 1
    return {'schema_version':1,'kind':'disk-usage','root':str(root),
            'file_count':count,'total_bytes':total,'largest_files':largest,
            'errors':errors,'complete':not stack and count < max_files and visited_dirs < max_files and errors == 0,
            'clean_allowed':False,
            'note':'Odczyt wskazanego katalogu. Wynik nie upoważnia do usuwania plików.'}

def can_clean(root,relative):
    root=Path(root).resolve()
    if root in temp_roots():return True
    known=profiles()
    if 'directx-cache' in known and root==Path(known['directx-cache']).resolve():return True
    if 'thumbnails' in known and root==Path(known['thumbnails']).resolve():
        return Path(relative).parent==Path('.') and Path(relative).name.startswith('thumbcache_') and Path(relative).suffix.lower()=='.db'
    return False

def scan(root,days=7):
    root=Path(root).resolve()
    if not 1<=days<=3650:raise ValueError('Wiek 1–3650 dni.')
    result=[]
    for path in files(root):
        st=path.stat()
        if st.st_mtime<time.time()-days*86400:
            relative=path.relative_to(root).as_posix()
            categories=[]
            if st.st_size>=100*1024*1024:categories.append('large')
            if path.suffix.lower() in ('.msi','.msix','.exe','.iso'):categories.append('installer_or_image')
            if path.suffix.lower() in ('.log','.etl','.evtx'):categories.append('log')
            result.append({'path':relative,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':digest(path),'categories':categories,'clean_allowed':can_clean(root,relative)})
    return {'schema_version':1,'root':str(root),'days':days,'files':result,'clean_allowed':bool(result) and all(row['clean_allowed'] for row in result),'total_bytes':sum(row['size'] for row in result)}

def clean(plan,destination):
    root=Path(plan['root']).resolve();destination=Path(destination).resolve()
    known=profiles()
    allowed_roots=temp_roots()+[Path(known[key]).resolve() for key in ('directx-cache','thumbnails') if key in known]
    if root not in allowed_roots:raise ValueError('CLEAN poza zatwierdzonym katalogiem.')
    if not isinstance(plan.get('files'),list) or any(not can_clean(root,row['path']) for row in plan['files']):raise ValueError('CLEAN dozwolone tylko dla zatwierdzonych plików TEMP/cache.')
    if not plan['files']:return {'moved':0,'quarantine':None}
    if destination.is_relative_to(root):raise ValueError('Kwarantanna musi być poza TEMP źródłowym.')
    # Wszystkie wpisy weryfikujemy przed pierwszą zmianą.
    for row in plan['files']:
        p=inside(root,row['path'])
        if not p.is_file() or p.stat().st_mtime>=time.time()-86400 or digest(p)!=row['sha256']:raise ValueError('Plan nieaktualny.')
    destination.mkdir(parents=True,exist_ok=False)
    manifest={'schema_version':1,'root':str(root),'files':[]}
    atomic_json(destination/'manifest.json',manifest)
    for row in plan['files']:
        source=inside(root,row['path'])
        if digest(source)!=row['sha256']:raise ValueError('Plik zmienił się przed przeniesieniem.')
        record={**row,'stored':uuid.uuid4().hex};manifest['files'].append(record)
        atomic_json(destination/'manifest.json',manifest)
        shutil.move(str(source),str(destination/record['stored']))
    return {'moved':len(manifest['files']),'quarantine':str(destination)}

def restore(directory):
    directory=Path(directory).resolve();data=read_json(directory/'manifest.json');root=Path(data['root']).resolve()
    if data.get('schema_version')!=1 or not isinstance(data.get('files'),list):raise ValueError('Nieprawidłowy manifest kwarantanny.')
    seen_paths=set();seen_stored=set()
    for row in data['files']:
        if not isinstance(row,dict):raise ValueError('Nieprawidłowy wpis kwarantanny.')
        target=str(inside(root,row['path'])).casefold();stored=str(inside(directory,row['stored'])).casefold()
        if target in seen_paths or stored in seen_stored:raise ValueError('Powtórzony wpis kwarantanny.')
        seen_paths.add(target);seen_stored.add(stored)
    if any(not can_clean(root,row['path']) for row in data['files']):raise ValueError('Nieprawidłowy root lub plik.')
    # Kolizje sprawdzamy przed pierwszym odtworzeniem.
    for row in data['files']:
        source=inside(directory,row['stored']);target=inside(root,row['path'])
        if source.exists() and (target.exists() or digest(source)!=row['sha256']):raise ValueError('Kolizja lub zmieniony plik kwarantanny.')
        if not source.exists() and (not target.is_file() or digest(target)!=row['sha256']):raise ValueError('Brakuje pliku kwarantanny i poprawnej odtworzonej kopii.')
    restored=0
    already_restored=0
    for row in data['files']:
        source=inside(directory,row['stored']);target=inside(root,row['path'])
        if not source.exists():
            if not target.is_file() or digest(target)!=row['sha256']:raise ValueError('Brakuje poprawnej odtworzonej kopii.')
            already_restored+=1;continue
        if target.exists() or digest(source)!=row['sha256']:raise ValueError('Kolizja lub zmieniony plik kwarantanny.')
        target.parent.mkdir(parents=True,exist_ok=True)
        with source.open('rb') as incoming,target.open('xb') as outgoing:
            shutil.copyfileobj(incoming,outgoing)
        if digest(target)!=row['sha256'] or digest(source)!=row['sha256']:raise ValueError('Plik zmienił się podczas odtwarzania; zachowano kwarantannę.')
        shutil.copystat(source,target);source.unlink();restored+=1
    return {'restored':restored,'already_restored':already_restored,'ok':True}
