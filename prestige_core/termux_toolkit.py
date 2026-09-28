from pathlib import Path
import os
import ipaddress
import sys
from .termux_runtime import atomic_json,digest,parser,read_json,run

CATEGORIES=['SYSTEM','NETWORK','FILES','GIT','SSH','ANDROID','BACKUP','DIAGNOSTICS']
OPERATIONS={'SYSTEM':['summary','uptime','storage'],'NETWORK':['addresses','routes','ping'],
    'FILES':['list','hash'],'GIT':['status','branches','last-commit'],'SSH':['algorithms'],
    'ANDROID':['battery','wifi'],'BACKUP':['create','verify'],'DIAGNOSTICS':['info','dependencies']}

def command(category,root,operation=None,target=None):
    root=str(Path(root).resolve())
    operation=operation or OPERATIONS.get(category,[''])[0]
    if operation not in OPERATIONS.get(category,[]):raise ValueError('Operacja nie należy do wybranej kategorii.')
    additional={('SYSTEM','uptime'):['uptime'],('SYSTEM','storage'):['df','-h'],
        ('NETWORK','routes'):['ip','route'],('GIT','branches'):['git','-C',root,'branch','--list'],
        ('GIT','last-commit'):['git','-C',root,'log','-1','--format=%h %s'],('ANDROID','wifi'):['termux-wifi-connectioninfo']}
    if (category,operation) in additional:return additional[(category,operation)]
    if category=='NETWORK' and operation=='ping':
        if not target:raise ValueError('Podaj --target IPv4/IPv6.')
        return ['ping','-c','4',str(ipaddress.ip_address(target))]
    commands={'SYSTEM':['uname','-a'],'NETWORK':['ip','address'],'FILES':['ls','-la','--',root],
       'GIT':['git','-C',root,'status','--short'],'SSH':['ssh','-Q','key'],'ANDROID':['termux-battery-status'],'DIAGNOSTICS':['termux-info']}
    if category not in commands:raise ValueError('Nieprawidłowa kategoria.')
    return commands[category]

def build():
    p=parser('Panel narzędzi Termux; korzysta z backendów systemowych.')
    p.add_argument('category',nargs='?',choices=CATEGORIES);p.add_argument('--menu',action='store_true')
    p.add_argument('--root',default='.');p.add_argument('--archive');p.add_argument('--apply',action='store_true')
    p.add_argument('--operation');p.add_argument('--target');p.add_argument('--file')
    return p

def handle(a):
    if a.menu:
        for i,name in enumerate(CATEGORIES,1):print(f'{i}. {name}',file=sys.stderr)
        print('0. Wyjście',file=sys.stderr);selection=input('Wybierz: ').strip()
        if selection=='0':return {'exit':True}
        if not selection.isdigit() or not 1<=int(selection)<=len(CATEGORIES):raise ValueError('Nieprawidłowy wybór.')
        a.category=CATEGORIES[int(selection)-1]
    if not a.category:return {'menu':CATEGORIES,'operations':OPERATIONS,'support':'--support'}
    operation=a.operation or OPERATIONS[a.category][0]
    if operation not in OPERATIONS[a.category]:raise ValueError('Operacja nie należy do kategorii.')
    if a.category=='FILES' and operation=='hash':
        if not a.file:raise ValueError('Podaj --file.')
        return {'file':str(Path(a.file).resolve()),'sha256':digest(a.file)}
    if a.category=='DIAGNOSTICS' and operation=='dependencies':
        import shutil
        return {name:bool(shutil.which(name)) for name in ('pkg','git','ssh','ip','ping','tar','termux-info','termux-battery-status','termux-wifi-connectioninfo')}
    if a.category=='BACKUP':
        if operation=='verify':
            if not a.archive:raise ValueError('Podaj --archive.')
            record=read_json(str(a.archive)+'.manifest.json')
            return {'archive':a.archive,'ok':digest(a.archive)==record['sha256']}
        source=Path(a.root).resolve()
        if not source.is_dir() or source.is_symlink() or not a.archive:raise ValueError('Wskaż folder i archive.')
        target=Path(a.archive).resolve()
        if target.is_relative_to(source) or target.exists():raise ValueError('Nowe archiwum musi być poza źródłem.')
        if Path(str(target)+'.manifest.json').exists():raise ValueError('Manifest docelowy już istnieje.')
        cmd=['tar','--exclude=.ssh','--exclude=.env*','--exclude=.git','--exclude=*token*','--exclude=*password*','--exclude=*secret*','--exclude=*.pem','--exclude=*.key','-czf',str(target),'-C',str(source),'.']
        if not a.apply:return {'plan':cmd}
        run(cmd,600)
        record={'schema_version':1,'sha256':digest(target),'size':target.stat().st_size}
        atomic_json(str(target)+'.manifest.json',record)
        return {'archive':str(target),**record}
    return {'category':a.category,'operation':operation,'result':run(command(a.category,a.root,operation,a.target),60)}
