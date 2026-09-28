from pathlib import Path
import json
import os
import shlex
import shutil
import subprocess
import sys

CATALOG={
 'system':('Diagnostyka Windows',['prestige-windows-toolkit','prestige-system-snapshot']),
 'security':('Bezpieczeństwo',['prestige-security-check','prestige-malware-triage']),
 'network':('Sieć',['prestige-internet-diagnostic','prestige-dns-benchmark','prestige-network-optimizer','prestige-nmap-profiles']),
 'monitoring':('Monitoring sieci',['prestige-netradar','prestige-lan-radar','prestige-network-snapshot']),
 'android':('Android / ADB',['prestige-adb-diagnostic','prestige-android-inspector']),
 'backup':('Backup',['prestige-backup']),
 'cleanup':('Czyszczenie',['prestige-pc-cleanup']),
 'files':('Analiza plików',['prestige-file-inspector','prestige-hash-checker']),
 'integrity':('Integralność',['prestige-integrity-monitor','prestige-folder-watch']),
 'report':('Raporty',['prestige-repair-report']),
 'service':('Narzędzia serwisowe',['prestige-usb-toolkit','prestige-termux-setup','prestige-termux-toolkit']),
 'ai':('AI Diagnostic Assistant',['prestige-ai-diagnostic-assistant']),
}

def tools():return [tool for _,items in CATALOG.values() for tool in items]

def resolve(root,tool):
    if tool not in tools():raise ValueError('Narzędzie spoza katalogu.')
    root=Path(root).resolve();directory=root/tool
    executable=root/(tool+'.exe')
    if executable.is_file() and not executable.is_symlink():
        executable.resolve().relative_to(root);return executable
    if directory.is_symlink():raise ValueError('Dowiązania narzędzi nie są obsługiwane.')
    script=directory/('prestige.ps1' if tool=='prestige-windows-toolkit' else 'app.py')
    if script.is_symlink() or not script.is_file():raise FileNotFoundError(f'Brak zainstalowanego narzędzia: {tool}')
    script.resolve().relative_to(root)
    return script

def launch(root,tool,arguments=()):
    script=resolve(root,tool)
    if script.suffix=='.exe':cmd=[str(script),'--backend']
    elif script.suffix=='.ps1':
        executable=shutil.which('pwsh')
        if not executable:raise FileNotFoundError('Wymagany PowerShell 7 (pwsh).')
        cmd=[executable,'-NoProfile','-File',str(script)]
    else:cmd=[sys.executable,str(script)]
    return subprocess.run(cmd+list(arguments),shell=False).returncode

def split_arguments(value):
    if os.name!='nt':return shlex.split(value)
    import ctypes
    from ctypes import wintypes
    parse=ctypes.windll.shell32.CommandLineToArgvW
    parse.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_int)];parse.restype=ctypes.POINTER(wintypes.LPWSTR)
    count=ctypes.c_int();pointer=parse('prestige '+value,ctypes.byref(count))
    if not pointer:raise ValueError('Nieprawidłowe argumenty.')
    try:return [pointer[i] for i in range(1,count.value)]
    finally:
        free=ctypes.windll.kernel32.LocalFree;free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p;free(pointer)

def menu(root):
    entries=list(CATALOG.items())
    while True:
        print('\nPRESTIGE TECH\nby Dominik Wasilak\n')
        for i,(_, (title,_)) in enumerate(entries,1):print(f'{i}. {title}')
        print('13. Ustawienia\n14. Wesprzyj autora\n0. Wyjście')
        choice=input('Wybierz: ').strip()
        if choice=='0':return 0
        if choice=='13':print('Katalog narzędzi:',root,'\nZmiana: uruchom z --tools-root.');continue
        if choice=='14':print('Opcja wsparcia autora zostanie udostępniona w przyszłości.');continue
        if not choice.isdigit() or not 1<=int(choice)<=len(entries):print('Nieprawidłowy wybór.');continue
        _,(_,items)=entries[int(choice)-1]
        for i,tool in enumerate(items,1):print(f'{i}. {tool}')
        selected=input('Narzędzie (0 — powrót): ').strip()
        if selected=='0':continue
        if not selected.isdigit() or not 1<=int(selected)<=len(items):print('Nieprawidłowy wybór.');continue
        tool=items[int(selected)-1]
        try:
            default=[] if tool=='prestige-windows-toolkit' else ['--help']
            raw=input('Argumenty (Enter — pomoc/lista modułów): ')
            code=launch(root,tool,split_arguments(raw) if raw.strip() else default)
            print('Kod zakończenia:',code)
        except (OSError,ValueError) as exc:print(str(exc))
