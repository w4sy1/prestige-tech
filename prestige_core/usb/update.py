"""Update selected USB tools with preserved data and rollback journal."""
from pathlib import Path
import shutil
import tempfile
import uuid
import re
from prestige_core.backup.runtime import atomic_json,digest,files,inside,read_json


def update(root,sources,prepare,execute=False):
    root=Path(root).resolve()
    if root.name!='PrestigeUSB' or not root.is_dir():raise ValueError('Wskaż istniejący katalog PrestigeUSB.')
    original=read_json(root/'manifest.json')
    if original.get('schema_version')!=1 or not isinstance(original.get('files'),dict):raise ValueError('Nieprawidłowy manifest zestawu.')
    sources=[Path(source).resolve() for source in sources]
    if not sources or len({source.name for source in sources})!=len(sources):raise ValueError('Wskaż różne narzędzia.')
    for source in sources:
        if not source.name.startswith('prestige-') or not source.is_dir():raise ValueError('Nieprawidłowe źródło.')
        target=inside(root,Path('Tools')/source.name)
        if not target.is_dir():raise ValueError('Aktualizacja wymaga już zainstalowanego narzędzia.')
        prefix=f'Tools/{source.name}/'
        managed={relative for relative in original['files'] if relative.startswith(prefix)}
        for relative in managed:
            path=inside(root,relative)
            if not path.is_file() or digest(path)!=original['files'][relative]:raise ValueError('Lokalnie zmienione narzędzie; najpierw uzgodnij zmiany.')
        # Unknown code/config is not discarded during replacement.
        for path in files(target):
            relative=path.relative_to(root).as_posix()
            if relative not in managed and path.relative_to(target).parts[0] not in ('logs','reports','__pycache__'):
                raise ValueError('Niezarządzany plik narzędzia wymaga ręcznego uzgodnienia.')
    if not execute:return {'operation':'UPDATE','tools':[source.name for source in sources],'executed':False,'backup':'Backup/Updates/<id>'}
    with tempfile.TemporaryDirectory(prefix='prestige-usb-update-') as temporary:
        prepared=prepare(temporary,sources)
        staging=Path(prepared['root'])
        manifest=read_json(staging/'manifest.json')
        journal_path=inside(root,Path('Backup/Updates')/uuid.uuid4().hex)
        journal_path.mkdir(parents=True,exist_ok=False)
        journal={'schema_version':1,'root':str(root),'original_manifest':original,'tools':[],'status':'PREPARED'}
        atomic_json(journal_path/'journal.json',journal)
        revised={**original,'files':dict(original['files']),'versions':dict(original.get('versions',{}))}
        for source in sources:
            name=source.name;target=inside(root,Path('Tools')/name);fresh=staging/'Tools'/name
            for folder in ('logs','reports'):
                previous=target/folder
                if previous.is_dir():shutil.copytree(previous,fresh/folder,dirs_exist_ok=True)
            record={'name':name,'installed_hashes':{key:value for key,value in manifest['files'].items() if key.startswith(f'Tools/{name}/')},'status':'PREPARED'}
            journal['tools'].append(record);atomic_json(journal_path/'journal.json',journal)
            shutil.move(str(target),str(journal_path/name))
            record['status']='BACKED_UP';atomic_json(journal_path/'journal.json',journal)
            shutil.move(str(fresh),str(target))
            record['status']='INSTALLED';atomic_json(journal_path/'journal.json',journal)
            revised['files']={key:value for key,value in revised['files'].items() if not key.startswith(f'Tools/{name}/')}
            revised['files'].update(record['installed_hashes']);revised['versions'][name]=manifest['versions'][name]
        journal['updated_manifest']=revised;atomic_json(journal_path/'journal.json',journal)
        atomic_json(root/'manifest.json',revised)
        journal['status']='COMPLETE';atomic_json(journal_path/'journal.json',journal)
        return {'executed':True,'tools':[source.name for source in sources],'rollback':str(journal_path),'ok':True}


def rollback(directory,execute=False):
    directory=Path(directory).resolve();journal=read_json(directory/'journal.json');root=Path(journal['root']).resolve()
    if root.name!='PrestigeUSB' or directory.parent!=inside(root,'Backup/Updates'):raise ValueError('Nieprawidłowy dziennik aktualizacji.')
    if journal.get('schema_version')!=1 or journal.get('status')=='ROLLED_BACK':raise ValueError('Nieaktywny dziennik.')
    current=read_json(root/'manifest.json')
    if current not in (journal['original_manifest'],journal.get('updated_manifest')):raise ValueError('Zestaw zmieniono po tej aktualizacji; cofnij najpierw nowszą.')
    for record in journal['tools']:
        name=record['name'];target=inside(root,Path('Tools')/name);saved=inside(directory,name)
        if not isinstance(name,str) or not re.fullmatch(r'prestige-[A-Za-z0-9_-]+',name):raise ValueError('Nieprawidłowa nazwa narzędzia w dzienniku.')
        prefix=f'Tools/{name}/'
        original_hashes={relative[len(prefix):]:expected for relative,expected in journal['original_manifest']['files'].items() if relative.startswith(prefix)}
        if not original_hashes:raise ValueError('Brak pierwotnego manifestu narzędzia.')
        original_location=saved if saved.is_dir() else target
        for relative,expected in original_hashes.items():
            file=inside(original_location,relative)
            if not file.is_file() or digest(file)!=expected:raise ValueError('Brak poprawnej kopii poprzedniej wersji; rollback odmówiony.')
        for file in files(original_location):
            relative=file.relative_to(original_location)
            if relative.as_posix() not in original_hashes and relative.parts[0] not in ('logs','reports','__pycache__'):
                raise ValueError('Niezarządzany plik w poprzedniej wersji; rollback odmówiony.')
        if not saved.exists():continue
        if target.exists():
            for relative,expected in record['installed_hashes'].items():
                file=inside(root,relative)
                if not file.is_file() or digest(file)!=expected:raise ValueError('Narzędzie zmieniono po aktualizacji; rollback odmówiony.')
    if not execute:return {'operation':'ROLLBACK','tools':[record['name'] for record in journal['tools']],'executed':False}
    for record in reversed(journal['tools']):
        name=record['name'];target=inside(root,Path('Tools')/name);saved=inside(directory,name)
        if not saved.exists():continue
        if target.exists():
            # Preserve new reports together with the retired version, without deleting data.
            shutil.move(str(target),str(inside(directory,name+'.retired-'+uuid.uuid4().hex)))
        shutil.move(str(saved),str(target))
    atomic_json(root/'manifest.json',journal['original_manifest'])
    journal['status']='ROLLED_BACK';atomic_json(directory/'journal.json',journal)
    return {'executed':True,'restored':True}
