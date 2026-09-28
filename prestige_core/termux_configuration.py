"""Transactional text configuration changes; private keys are never read or copied."""
from pathlib import Path
import hashlib
import os
import re
import uuid
from .termux_runtime import atomic_json,digest,inside,read_json

BLOCK='\n# BEGIN PRESTIGE TECH\nexport PATH="$HOME/scripts:$HOME/tools:$PATH"\nalias ll="ls -alF"\nalias py="python"\nalias gs="git status"\n# END PRESTIGE TECH\n'
SSH_BLOCK='\n# BEGIN PRESTIGE TECH SSH\nHost *\n    ServerAliveInterval 60\n    ServerAliveCountMax 3\n# END PRESTIGE TECH SSH\n'
ALLOWED={'.bashrc','.gitconfig','.ssh/config'}
FOLDERS=['projects','tools','scripts','logs','backup']


def atomic_text(path,text):
    path=Path(path);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    mode=(path.stat().st_mode & 0o777) if path.exists() else 0o600
    descriptor=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY,mode)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8',newline='') as stream:
            stream.write(text);stream.flush();os.fsync(stream.fileno())
        os.chmod(temporary,mode);os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)

def quote_git(value):
    if not value or len(value)>256 or any(c in value for c in '\r\n\0'):raise ValueError('Nieprawidłowa tożsamość Git.')
    return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'

def configure(home,git_name=None,git_email=None,ssh_client=False):
    home=Path(home).resolve();planned={}
    def text(relative):
        p=inside(home,relative)
        return p.read_text(encoding='utf-8') if p.exists() else None
    original=text('.bashrc')
    if '# BEGIN PRESTIGE TECH' not in (original or ''):planned['.bashrc']=((original or '')+BLOCK,original)
    if bool(git_name)!=bool(git_email):raise ValueError('Podaj razem nazwę i e-mail Git.')
    if git_name:
        original=text('.gitconfig')
        block='\n[user]\n\tname = '+quote_git(git_name)+'\n\temail = '+quote_git(git_email)+'\n'
        if not (original or '').endswith(block):planned['.gitconfig']=((original or '')+block,original)
    if ssh_client:
        original=text('.ssh/config')
        if '# BEGIN PRESTIGE TECH SSH' not in (original or ''):planned['.ssh/config']=((original or '')+SSH_BLOCK,original)
    if not planned:return {'changed':False,'reason':'Żądana konfiguracja już istnieje.'}
    backup=inside(home,'backup')/('prestige-'+uuid.uuid4().hex);backup.mkdir(parents=True,mode=0o700)
    records=[]
    for relative,(new,old) in planned.items():
        records.append({'file':relative,'original':old,'after_sha256':hashlib.sha256(new.encode('utf-8')).hexdigest()})
    manifest={'schema_version':2,'files':records,'complete':False};atomic_json(backup/'manifest.json',manifest)
    os.chmod(backup/'manifest.json',0o600)
    for relative,(new,old) in planned.items():
        p=inside(home,relative);p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        atomic_text(p,new)
        if old is None and relative=='.ssh/config':os.chmod(p,0o600)
    for folder in FOLDERS:inside(home,folder).mkdir(exist_ok=True)
    manifest['complete']=True;atomic_json(backup/'manifest.json',manifest);os.chmod(backup/'manifest.json',0o600)
    return {'changed':True,'files':list(planned),'backup':str(backup),'ssh':'Konfiguracja klienta; sshd nie jest uruchamiany, klucze prywatne nie są odczytywane.'}

def restore(home,backup):
    home=Path(home).resolve();backup=Path(backup).resolve();backup.relative_to(home/'backup')
    data=read_json(backup/'manifest.json')
    rows=data['files'] if data.get('schema_version')==2 else [data]
    if not isinstance(rows,list):raise ValueError('Błędny manifest.')
    restore_rows=[]
    for row in rows:
        if row.get('file') not in ALLOWED:raise ValueError('Niedozwolony plik.')
        p=inside(home,row['file']);original=row['original']
        if original is not None and not isinstance(original,str):raise ValueError('Nieprawidłowa kopia.')
        if not p.exists() and original is None:continue
        if p.exists() and original is not None and p.read_text(encoding='utf-8')==original:continue
        if not p.is_file() or digest(p)!=row['after_sha256']:raise ValueError('Konfiguracja zmieniona po operacji; rollback odmówiony.')
        restore_rows.append((p,original))
    for p,original in restore_rows:
        if original is None:p.unlink()
        else:
            atomic_text(p,original)
    return {'restored':True,'files':len(restore_rows),'packages':'Pakiety pozostają zainstalowane.'}
