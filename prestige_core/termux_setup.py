from .termux_configuration import configure,restore
from pathlib import Path
import os
import shutil
import sys
import uuid
from .termux_runtime import parser,run

PROFILES={
 'minimal':['git','python','curl','nano'],
 'developer':['git','python','curl','nano','vim','tmux','jq','zip','unzip'],
 'network':['git','python','curl','wget','openssh','dnsutils','nmap','jq'],
 'security':['git','python','curl','openssh','dnsutils','nmap','jq','openssl'],
}
PROFILES['full']=sorted({p for values in PROFILES.values() for p in values})
FOLDERS=['projects','tools','scripts','logs','backup']
BLOCK='\n# BEGIN PRESTIGE TECH\nexport PATH="$HOME/scripts:$HOME/tools:$PATH"\nalias ll="ls -alF"\nalias py="python"\nalias gs="git status"\n# END PRESTIGE TECH\n'



def build():
    p=parser('Konfiguracja Termuxa. Domyślnie tylko plan.')
    p.add_argument('--profile',choices=PROFILES,default='minimal')
    p.add_argument('--apply',action='store_true',help='Zainstaluj pakiety i zmień konfigurację')
    p.add_argument('--rollback',help='Katalog kopii konfiguracji')
    p.add_argument('--git-name',help='Opcjonalna nazwa użytkownika Git')
    p.add_argument('--git-email',help='Opcjonalny e-mail Git; wymaga --git-name')
    p.add_argument('--ssh-client',action='store_true',help='Dodaj blok keepalive klienta SSH z kopią konfiguracji')
    return p

def handle(args):
    if bool(args.git_name)!=bool(args.git_email):raise ValueError('Podaj razem --git-name i --git-email.')
    plan={'packages':PROFILES[args.profile],'folders':FOLDERS,'changes':['Blok PATH i aliasów w .bashrc'],'git_identity_requested':bool(args.git_name),'ssh_client_requested':args.ssh_client,'rollback':args.rollback}
    if not args.apply:return {'dry_run':True,'plan':plan}
    prefix=os.environ.get('PREFIX','')
    if 'com.termux' not in prefix or not shutil.which('pkg'):raise OSError('Wymagany Termux z pkg.')
    home=Path.home()
    if args.rollback:return restore(home,args.rollback)
    result=configure(home,args.git_name,args.git_email,args.ssh_client)
    run(['pkg','install','-y',*PROFILES[args.profile]],timeout=900)
    return {**result,'packages':PROFILES[args.profile]}
