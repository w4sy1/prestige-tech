"""Explicit service exports. No password stores or browser profile copying."""
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from .runtime import atomic_json, digest, files, powershell, read_json, run


def known_folders():
    if os.name != 'nt':
        return {name: str(Path.home() / name) for name in ('Desktop', 'Documents', 'Pictures', 'Downloads')}
    return powershell(r'''$s=New-Object -ComObject Shell.Application
$r=[ordered]@{};foreach($pair in @(@('Desktop','shell:Desktop'),@('Documents','shell:Personal'),@('Pictures','shell:My Pictures'),@('Downloads','shell:Downloads'))){$folder=$s.NameSpace($pair[1]);if($folder){$r[$pair[0]]=$folder.Self.Path}}
$r|ConvertTo-Json''')


def clean_bookmarks(node, depth=0):
    if depth > 50 or not isinstance(node, dict):
        raise ValueError('Nieprawidłowe drzewo zakładek.')
    result = {'name': str(node.get('name', ''))[:1000]}
    if node.get('type') == 'url':
        url = urlsplit(str(node.get('url', '')))
        if url.scheme not in ('http', 'https') or not url.hostname:
            return None
        host = '[' + url.hostname + ']' if ':' in url.hostname else url.hostname
        if url.port:
            host += ':' + str(url.port)
        result.update(type='url', url=urlunsplit((url.scheme, host, url.path, '', '')))
    else:
        children = node.get('children', [])
        if not isinstance(children, list):
            raise ValueError('Nieprawidłowe zakładki.')
        result.update(type='folder', children=[clean for child in children if (clean := clean_bookmarks(child, depth+1)) is not None])
    return result


def export_service(destination, system=False, drivers=False, bookmarks=None):
    destination = Path(destination)
    folder = destination / '_service'
    folder.mkdir(exist_ok=False)
    errors = []
    if system:
        try:
            data = powershell(r'''$r=[ordered]@{}
$r.applications=@(Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | Where-Object DisplayName | Select-Object DisplayName,DisplayVersion,Publisher | Sort-Object DisplayName,DisplayVersion -Unique)
$r.windows=Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture
$r.network=@(Get-NetIPConfiguration | Select-Object InterfaceAlias,@{n='IPv4';e={$_.IPv4Address.IPAddress}},@{n='Gateway';e={$_.IPv4DefaultGateway.NextHop}},@{n='DNS';e={$_.DNSServer.ServerAddresses}})
$r.drivers=@(Get-CimInstance Win32_PnPSignedDriver | Select-Object DeviceName,DriverVersion,DriverProviderName,InfName,IsSigned)
$r|ConvertTo-Json -Depth 6''', 180)
            atomic_json(folder / 'system.json', data)
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append({'export': 'system', 'error': type(exc).__name__})
    if drivers:
        try:
            target = folder / 'drivers'
            target.mkdir()
            run(['pnputil.exe', '/export-driver', '*', str(target)], timeout=600)
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append({'export': 'drivers', 'error': type(exc).__name__})
    for index, source in enumerate(bookmarks or []):
        try:
            if Path(source).suffix.lower() in ('.sqlite','.db'):
                connection=sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro',uri=True)
                try:
                    rows=connection.execute('SELECT b.title,p.url FROM moz_bookmarks b JOIN moz_places p ON p.id=b.fk WHERE b.type=1 ORDER BY b.id').fetchmany(100001)
                    if len(rows)>100000:raise ValueError('Zbyt wiele zakładek.')
                    data={'roots':{'firefox':{'type':'folder','name':'Firefox','children':[{'type':'url','name':title or '', 'url':url} for title,url in rows]}}}
                finally:connection.close()
            else:data = read_json(source)
            if not isinstance(data, dict) or not isinstance(data.get('roots'), dict):
                raise ValueError('Wskaż plik Bookmarks Chromium, nie cały profil.')
            cleaned = {key: clean_bookmarks(value) for key, value in data['roots'].items()}
            atomic_json(folder / f'bookmarks-{index+1}.json', {'roots': cleaned,
                'note': 'Pominięto dane logowania, query i fragment URL oraz schematy inne niż HTTP/HTTPS.'})
        except (OSError, RuntimeError, ValueError, TypeError, sqlite3.Error) as exc:
            errors.append({'export': 'bookmarks', 'index': index+1, 'error': type(exc).__name__})
    entries = [{'path': path.relative_to(destination).as_posix(), 'sha256': digest(path), 'size': path.stat().st_size} for path in files(folder)]
    return entries, errors
