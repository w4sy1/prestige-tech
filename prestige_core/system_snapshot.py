from pathlib import Path
import json
import os
from datetime import datetime, timezone

from .security_check import _powershell

QUERIES={
 'hardware':'Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory',
 'windows':'Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber',
 'updates':'Get-HotFix | Select-Object HotFixID,InstalledOn',
 'programs':"Get-ItemProperty 'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*','HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*','HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*' -ErrorAction SilentlyContinue | Where-Object DisplayName | Select-Object @{n='RegistryKey';e={$_.PSPath}},DisplayName,DisplayVersion,Publisher",
 'services':'Get-Service | Select-Object Name,Status,StartType',
 'processes':'Get-Process | Select-Object Id,ProcessName,Path',
 'startup':'Get-CimInstance Win32_StartupCommand | Select-Object Name,Location',
 'tasks':'Get-ScheduledTask | Select-Object TaskName,TaskPath,State',
 'network':'Get-NetIPAddress | Select-Object InterfaceAlias,IPAddress,AddressFamily,PrefixLength',
 'security':'Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled',
 'disk':'Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,Size,FreeSpace,FileSystem',
 'drivers':'Get-CimInstance Win32_PnPSignedDriver | Select-Object DeviceID,DeviceName,DriverVersion,DriverProviderName,IsSigned',
}

IDENTITIES={'programs':('RegistryKey',),'services':('Name',),'tasks':('TaskPath','TaskName'),
    'updates':('HotFixID',),'disk':('DeviceID',),'drivers':('DeviceID',),'network':('InterfaceAlias','IPAddress'),
    'startup':('Name','Location')}

def keyed_changes(section,before,after):
    fields=IDENTITIES.get(section)
    if not fields:return None
    def index(rows):
        result={}
        for row in rows:
            if not isinstance(row,dict) or any(row.get(field) is None for field in fields):return None
            key=tuple(str(row[field]).casefold() for field in fields)
            if key in result:return None
            result[key]=row
        return result
    left,right=index(before),index(after)
    if left is None or right is None:return None
    return {'identity_fields':fields,'added':[right[key] for key in sorted(right.keys()-left.keys())],
        'removed':[left[key] for key in sorted(left.keys()-right.keys())],
        'modified':[{'identity':dict(zip(fields,key)),'before':left[key],'after':right[key],
            'changed_fields':sorted(field for field in left[key].keys()|right[key].keys() if left[key].get(field)!=right[key].get(field))}
            for key in sorted(left.keys()&right.keys()) if left[key]!=right[key]]}

def collect(*, runner=None, platform=None):
    if (platform or os.name) != 'nt':
        raise RuntimeError('System Snapshot wymaga Windows.')
    parts=[]
    for name,query in QUERIES.items():
        parts.append(f"try{{$r['{name}']=@{{status='OK';data=@({query})}}}}catch{{$r['{name}']=@{{status='UNKNOWN';data=@();error=$_.Exception.GetType().Name}}}}")
    if runner is None:
        sections = _powershell('$r=[ordered]@{};'+';'.join(parts)+';$r|ConvertTo-Json -Depth 6',180)
    else:
        sections = _powershell('$r=[ordered]@{};'+';'.join(parts)+';$r|ConvertTo-Json -Depth 6',180,runner=runner)
    if not isinstance(sections, dict):
        raise RuntimeError('System Snapshot zwrócił nieprawidłowe sekcje.')
    return {'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),'sections':sections}


def validate_snapshot(data):
    if (not isinstance(data,dict) or data.get('schema_version') != 1
            or not isinstance(data.get('sections'),dict)):
        raise ValueError('Nieobsługiwany snapshot.')
    for name in QUERIES:
        row=data['sections'].get(name)
        if not isinstance(row,dict) or row.get('status') not in ('OK','UNKNOWN'):
            raise ValueError('Snapshot ma brakującą lub nieprawidłową sekcję: '+name)
        if not isinstance(row.get('data'),list):
            raise ValueError('Snapshot ma nieprawidłowe dane: '+name)
    return data


def save_snapshot(data,path):
    validate_snapshot(data)
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    return str(Path(path).resolve())


def load_snapshot(path,*,max_bytes=64*1024*1024):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>max_bytes:
        raise ValueError('Wymagany zwykły snapshot JSON do 64 MiB.')
    return validate_snapshot(json.loads(path.read_text(encoding='utf-8-sig')))

def compare(before,after):
    before,after=validate_snapshot(before),validate_snapshot(after)
    changes={}
    for section in sorted(before['sections'].keys()|after['sections'].keys()):
        a=before['sections'].get(section,{});b=after['sections'].get(section,{})
        if a.get('status')!='OK' or b.get('status')!='OK':changes[section]={'status':'UNKNOWN'};continue
        left={json.dumps(row,sort_keys=True,ensure_ascii=False) for row in a['data']}
        right={json.dumps(row,sort_keys=True,ensure_ascii=False) for row in b['data']}
        changes[section]={'status':'COMPARED','removed_or_previous':[json.loads(x) for x in sorted(left-right)],'new_or_updated':[json.loads(x) for x in sorted(right-left)]}
        identified=keyed_changes(section,a['data'],b['data'])
        if identified is not None:changes[section]['identified_changes']=identified
    return {'sections':changes,'note':'Zmiana wiersza pokazana jako poprzedni i nowy stan. Procesy i wolne miejsce naturalnie zmieniają się w czasie.'}
