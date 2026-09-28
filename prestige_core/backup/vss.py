"""Explicit Windows VSS backup wrapper; deletes only snapshots created by this run."""
from pathlib import Path,PureWindowsPath
import os
import re
import subprocess
import uuid
from .runtime import atomic_json,powershell


def drive(source):
    value=PureWindowsPath(source).drive
    if not re.fullmatch(r'[A-Za-z]:',value):raise ValueError('VSS wymaga lokalnej ścieżki z literą dysku.')
    return value.upper()+'\\'


def create(volume):
    if not re.fullmatch(r'[A-Z]:\\',volume):raise ValueError('Nieprawidłowy wolumin.')
    script=f"$result=Invoke-CimMethod -ClassName Win32_ShadowCopy -MethodName Create -Arguments @{{Volume='{volume}';Context='ClientAccessible'}};if($result.ReturnValue -ne 0){{throw ('VSS Create failed: '+$result.ReturnValue)}};$copy=Get-CimInstance Win32_ShadowCopy | Where-Object ID -eq $result.ShadowID;[pscustomobject]@{{id=$copy.ID;device=$copy.DeviceObject}}|ConvertTo-Json"
    return powershell(script,120)


def remove(identifier):
    normalized=str(uuid.UUID(identifier.strip('{}')))
    powershell("Get-CimInstance Win32_ShadowCopy | Where-Object ID -eq '{"+normalized+"}' | Remove-CimInstance;@{removed=$true}|ConvertTo-Json",90)


def backup(sources,destination,copy_function,**options):
    if os.name!='nt':raise ValueError('VSS wymaga Windows i uprawnień administratora.')
    sources=[str(Path(source).resolve()) for source in sources];volumes={drive(source) for source in sources}
    if not sources:raise ValueError('VSS wymaga co najmniej jednego folderu źródłowego.')
    destination=Path(destination).resolve()
    if destination.exists() or any(destination.is_relative_to(Path(source)) for source in sources):raise ValueError('Wymagany nowy folder backupu poza źródłami.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    journal=destination.parent/('vss-'+uuid.uuid4().hex+'.json');state={'schema_version':1,'snapshots':{},'cleanup_errors':[],'status':'PREPARING'}
    atomic_json(journal,state)
    result=None
    try:
        for volume in sorted(volumes):
            state['snapshots'][volume]=create(volume);atomic_json(journal,state)
        mapped=[]
        for source in sources:
            item=state['snapshots'][drive(source)];device=item.get('device','')
            if not re.fullmatch(r'\\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy\d+',device):raise ValueError('VSS zwrócił nieprawidłową ścieżkę urządzenia.')
            mapped.append(device+'\\'+str(PureWindowsPath(source).relative_to(PureWindowsPath(source).anchor)))
        state['status']='COPYING';atomic_json(journal,state)
        result=copy_function(mapped,destination,**options)
        result['vss_journal']=str(journal)
        return result
    finally:
        for item in state['snapshots'].values():
            try:remove(item['id']);item['removed']=True
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:state['cleanup_errors'].append({'id':item.get('id'),'error':type(exc).__name__})
        state['status']='CLEANUP_REQUIRED' if state['cleanup_errors'] else 'CLOSED';atomic_json(journal,state)
        if result is not None:
            result['vss_cleanup_required']=bool(state['cleanup_errors'])
            if state['cleanup_errors']:result['ok']=False


def recover(journal,execute=False):
    from .runtime import read_json
    state=read_json(journal)
    if state.get('schema_version')!=1 or not isinstance(state.get('snapshots'),dict):raise ValueError('Nieprawidłowy dziennik VSS.')
    remaining=[item['id'] for item in state['snapshots'].values() if not item.get('removed')]
    for identifier in remaining:uuid.UUID(identifier.strip('{}'))
    if not execute:return {'plan':'Usuń wyłącznie migawki wymienione w tym dzienniku','snapshots':remaining}
    for item in state['snapshots'].values():
        if not item.get('removed'):remove(item['id']);item['removed']=True;atomic_json(journal,state)
    state['cleanup_errors']=[];state['status']='CLOSED';atomic_json(journal,state)
    return {'removed':len(remaining)}
