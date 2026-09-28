from pathlib import Path
import re
import shutil
import sys
import uuid
from .service import export_service,known_folders
from .runtime import atomic_json,digest,entry,files,inside,parser,read_json

DENY=re.compile(r'(?i)(^\.env($|\.)|password|passwd|credential|cookie|token|secret|login data|web data|^id_(rsa|ed25519|ecdsa)|^\.ssh$|^\.aws$|^\.azure$|^\.gnupg$|^\.git$|^appdata$)')
def allowed(path):
    return not any(DENY.search(p) for p in Path(path).parts) and Path(path).suffix.lower() not in ('.pem','.key','.pfx','.p12','.kdbx')

def plan(sources):
    result=[];skipped=0
    for index,source in enumerate(sources):
        root=Path(source).resolve()
        for path in files(root):
            relative=path.relative_to(root)
            if not allowed(relative):skipped+=1;continue
            result.append({'source':str(path),'relative':f'{index+1}-{root.name}/{relative.as_posix()}','size':path.stat().st_size})
    return {'files':result,'excluded_count':skipped,'total_bytes':sum(p['size'] for p in result)}

def backup(sources,destination,system=False,drivers=False,bookmarks=None,preserve_acl=False):
    destination=Path(destination).resolve()
    for source in sources:
        if destination.is_relative_to(Path(source).resolve()):raise ValueError('Backup nie może być wewnątrz źródła.')
    data=plan(sources);destination.mkdir(parents=True,exist_ok=False)
    entries=[];errors=[]
    atomic_json(destination/'manifest.json',{'schema_version':1,'files':entries,'errors':errors,'complete':False})
    for index,item in enumerate(data['files']):
        target=inside(destination,item['relative']);target.parent.mkdir(parents=True,exist_ok=True)
        try:
            source=Path(item['source']);before=source.stat()
            if source.is_symlink():raise ValueError('Źródło stało się dowiązaniem.')
            shutil.copy2(source,target)
            value=digest(target);after=source.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or value!=digest(source):
                target.unlink();raise ValueError('Zmiana źródła podczas kopii.')
            entries.append({'path':item['relative'],'sha256':value,'size':target.stat().st_size})
        except (OSError,ValueError) as exc:errors.append({'path':item['relative'],'error':type(exc).__name__})
        atomic_json(destination/'manifest.json',{'schema_version':1,'files':entries,'errors':errors,'complete':False})
        if (index+1)%100==0:print(f'Postęp: {index+1}/{len(data["files"])}',file=sys.stderr)
    if system or drivers or bookmarks:
        atomic_json(destination/'manifest.json',{'schema_version':1,'files':entries,'errors':errors,'complete':False})
        extra, export_errors = export_service(destination,system,drivers,bookmarks)
        entries.extend(extra);errors.extend(export_errors)
        atomic_json(destination/'manifest.json',{'schema_version':1,'files':entries,'errors':errors,'complete':False})
    if preserve_acl:
        from .acl import capture
        atomic_json(destination/'manifest.json',{'schema_version':1,'files':entries,'errors':errors,'complete':False})
        record=capture([row for row in data['files'] if row['relative'] in {item['path'] for item in entries}])
        metadata_path=destination/'_service/acl.json';atomic_json(metadata_path,record)
        entries.append({'path':'_service/acl.json','sha256':digest(metadata_path),'size':metadata_path.stat().st_size})
        if any(row.get('status')=='UNKNOWN' for row in record['entries']):errors.append({'export':'acl','error':'PARTIAL'})
    atomic_json(destination/'manifest.json',{'schema_version':1,'files':entries,'errors':errors,'complete':not errors})
    return {'copied':len(entries),'excluded':data['excluded_count'],'errors':errors,'ok':not errors,'destination':str(destination)}

def verify(directory):
    directory=Path(directory);data=load_manifest(directory)
    problems=[]
    for item in data['files']:
        p=inside(directory,item['path'])
        if not p.is_file():problems.append({'path':item['path'],'status':'MISSING'})
        elif digest(p).lower()!=item['sha256'].lower():problems.append({'path':item['path'],'status':'CHANGED'})
        elif 'size' in item and p.stat().st_size!=item['size']:problems.append({'path':item['path'],'status':'SIZE_MISMATCH'})
    return {'problems':problems,'complete':data.get('complete') is True,'backup_errors':data.get('errors',[]),
        'ok':not problems and data.get('complete') is True and not data.get('errors')}

def load_manifest(directory):
    data=read_json(Path(directory)/'manifest.json')
    if not isinstance(data,dict) or data.get('schema_version')!=1 or not isinstance(data.get('files'),list):
        raise ValueError('Nieprawidłowy manifest.')
    if not isinstance(data.get('complete'),bool) or not isinstance(data.get('errors',[]),list):
        raise ValueError('Nieprawidłowy stan manifestu.')
    seen=set()
    for item in data['files']:
        if not isinstance(item,dict) or not isinstance(item.get('path'),str) or not re.fullmatch('[a-fA-F0-9]{64}',str(item.get('sha256',''))):
            raise ValueError('Nieprawidłowy wpis manifestu.')
        if 'size' in item and (type(item['size']) is not int or item['size']<0):raise ValueError('Nieprawidłowy rozmiar pliku.')
        path=inside(directory,item['path'])
        normalized=str(path).casefold()
        if normalized in seen:raise ValueError('Powtórzona ścieżka manifestu.')
        seen.add(normalized)
    return data

def restore(directory,destination,apply=False,restore_acl=False):
    directory=Path(directory).resolve();destination=Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(directory):
        raise ValueError('Odtwarzanie wymaga nowego katalogu poza backupem.')
    data=load_manifest(directory)
    if restore_acl and not any(item['path']=='_service/acl.json' for item in data['files']):raise ValueError('Kopia nie zawiera danych ACL.')
    check=verify(directory)
    if not check['ok']:raise ValueError('Backup jest niekompletny lub uszkodzony.')
    if not apply:return {'operation':'RESTORE','destination':str(destination),'files':len(data['files']),'executed':False}
    destination.mkdir(parents=True,exist_ok=False)
    copied=0;errors=[]
    journal=destination.parent/('prestige-restore-'+uuid.uuid4().hex+'.json')
    state={'schema_version':1,'operation':'RESTORE','source':str(directory),'destination':str(destination),
        'status':'IN_PROGRESS','copied':0,'total':len(data['files']),'errors':[]}
    atomic_json(journal,state)
    for item in data['files']:
        try:
            source=inside(directory,item['path']);target=inside(destination,item['path'])
            target.parent.mkdir(parents=True,exist_ok=True)
            with source.open('rb') as source_file,target.open('xb') as target_file:
                shutil.copyfileobj(source_file,target_file)
            if digest(target).lower()!=item['sha256'].lower():
                target.unlink();raise ValueError('Źródło zmieniło się podczas odtwarzania.')
            shutil.copystat(source,target);copied+=1
        except (OSError,ValueError) as exc:
            errors.append({'path':item['path'],'error':type(exc).__name__})
        state.update(copied=copied,errors=errors);atomic_json(journal,state)
    acl_result=None
    if restore_acl and not errors:
        from .acl import restore as restore_permissions
        acl_file=destination/'_service/acl.json'
        if not any(item['path']=='_service/acl.json' for item in data['files']):raise ValueError('Kopia nie zawiera zweryfikowanych danych ACL.')
        acl_result=restore_permissions(destination,read_json(acl_file))
        if not acl_result['ok']:errors.append({'stage':'restore-acl','errors':acl_result['errors']})
    state.update(status='FAILED' if errors else 'COMPLETE',copied=copied,errors=errors);atomic_json(journal,state)
    return {'destination':str(destination),'copied':copied,'errors':errors,'acl':acl_result,'executed':True,'ok':not errors,'journal':str(journal)}

def build():
    p=parser('Backup do nowego katalogu. Filtry wykluczają znane magazyny sekretów.')
    p.add_argument('command',nargs='?',choices=['plan','backup','verify','restore','folders','vss-recover'])
    p.add_argument('--vss',action='store_true',help='Windows: kopia z migawek VSS; wymaga administratora')
    p.add_argument('--vss-journal',help='Dziennik pozostałych migawek po przerwaniu backupu')
    p.add_argument('--preserve-acl',action='store_true',help='Zapisz dodatkowo ACL/tryb plików w manifeście')
    p.add_argument('--restore-acl',action='store_true',help='Odtwarzanie: zastosuj DACL/tryb z kopii do nowych plików')
    p.add_argument('--source',action='append');p.add_argument('--destination');p.add_argument('--apply',action='store_true')
    p.add_argument('--standard-folder',action='append',choices=['Desktop','Documents','Pictures','Downloads'])
    p.add_argument('--system-export',action='store_true',help='Lista aplikacji, sterowników i podstawowa konfiguracja Windows')
    p.add_argument('--drivers',action='store_true',help='Eksport pakietów sterowników przez pnputil')
    p.add_argument('--bookmarks',action='append',help='Konkretny plik Bookmarks Chromium; bez całego profilu')
    p.add_argument('--restore-to',help='Nowy katalog odtwarzania')
    return p

def handle(a):
    if a.command=='vss-recover':
        if not a.vss_journal:raise ValueError('Podaj --vss-journal.')
        from .vss import recover
        return recover(a.vss_journal,a.apply)
    if a.command=='folders':return known_folders()
    if a.command=='restore':
        if not a.destination or not a.restore_to:raise ValueError('Podaj --destination (backup) i --restore-to (nowy folder).')
        return restore(a.destination,a.restore_to,a.apply,a.restore_acl)
    if a.standard_folder:
        known=known_folders();a.source=(a.source or [])+[known[name] for name in a.standard_folder]
    if a.command=='verify':
        if not a.destination:raise ValueError('Podaj destination.')
        return verify(a.destination)
    if not a.source and not (a.system_export or a.drivers or a.bookmarks):raise ValueError('Wskaż foldery lub eksport serwisowy.')
    a.source=a.source or []
    if a.command=='plan' or (a.command=='backup' and not a.apply):return dict(plan(a.source),exports={'system':a.system_export,'drivers':a.drivers,'bookmarks_count':len(a.bookmarks or [])})
    if a.command=='backup' and a.destination:
        if a.vss:
            from .vss import backup as vss_backup
            return vss_backup(a.source,a.destination,backup,system=a.system_export,drivers=a.drivers,bookmarks=a.bookmarks,preserve_acl=a.preserve_acl)
        return backup(a.source,a.destination,a.system_export,a.drivers,a.bookmarks,a.preserve_acl)
    raise ValueError('Wybierz polecenie i destination.')

if __name__=='__main__':sys.exit(entry(build,handle))
