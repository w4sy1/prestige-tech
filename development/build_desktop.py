"""Build independent single-file Windows executables and a combined portable ZIP."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def verify_output(project,output,cached=False):
    work=ROOT/'build/desktop'/project.name;work.mkdir(parents=True,exist_ok=True)
    for args in (['--schema'],['--smoke'],['--backend','-Command','modules'] if (project/'prestige.ps1').exists() else ['--backend','--help']):
        result=subprocess.run([str(output),*args],cwd=output.parent,capture_output=True,timeout=90)
        if result.returncode:
            (work/'failure.txt').write_bytes(result.stdout+b'\n'+result.stderr)
            raise RuntimeError('EXE startup failed: '+project.name+'; '+str(work/'failure.txt'))
    return {'project':project.name,'executable':str(output),'bytes':output.stat().st_size,
        'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'startup_checks':3,'passed':True,'cached':cached}

def build(project,version,force=False):
    destination=ROOT/'dist'/('desktop-'+version);destination.mkdir(parents=True,exist_ok=True)
    output=destination/(project.name+'.exe')
    if output.exists() and not force:return verify_output(project,output,cached=True)
    work=ROOT/'build/desktop'/project.name;work.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--onefile','--console','--name',project.name,
        '--distpath',str(destination),'--workpath',str(work/'work'),'--specpath',str(work),
        '--paths',str(project),'--hidden-import','pdf_export','--collect-all','reportlab',
        '--add-data',str(project/'metadata.json')+';.', '--add-data',str(project/'config')+';config',
        '--add-data',str(project/'assets')+';assets', '--add-data',str(project/'LICENSE')+';.', '--add-data',str(project/'THIRD_PARTY_NOTICES.txt')+';.']
    if (project/'app.py').exists():command+=['--hidden-import','app']
    if (project/'prestige.ps1').exists():command+=['--add-data',str(project/'prestige.ps1')+';.', '--add-data',str(project/'src')+';src']
    if (project/'prestige_cli').exists():command+=['--add-data',str(project/'prestige_cli/author.json')+';prestige_cli']
    command.append(str(project/'gui.py'))
    with (work/'build.log').open('w',encoding='utf-8') as log:
        process=subprocess.run(command,cwd=project,stdout=log,stderr=subprocess.STDOUT,timeout=900)
    if process.returncode:raise RuntimeError('Build failed: '+project.name+'; '+str(work/'build.log'))
    return verify_output(project,output)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',action='append');parser.add_argument('--version',default='0.3.0')
    parser.add_argument('--workers',type=int,default=2);parser.add_argument('--force',action='store_true');args=parser.parse_args()
    projects=[path for path in sorted(ROOT.glob('prestige-*')) if (path/'gui.py').exists() and (not args.project or path.name in args.project)]
    results=[]
    with ThreadPoolExecutor(max_workers=max(1,min(args.workers,3))) as executor:
        for result in executor.map(lambda project:build(project,args.version,args.force),projects):
            results.append(result);print(result['project']+': EXE OK',flush=True)
    (ROOT/'development/desktop-build.json').write_text(json.dumps({'version':args.version,'results':results},indent=2),encoding='utf-8')
    if args.project:return
    destination=ROOT/'dist'/('desktop-'+args.version)
    shutil.copy2(ROOT/'LICENSE',destination/'LICENSE')
    shutil.copy2(ROOT/'prestige-hash-checker/THIRD_PARTY_NOTICES.txt',destination/'THIRD_PARTY_NOTICES.txt')
    shutil.copy2(ROOT/'prestige-hash-checker/assets/FONT-LICENSE.txt',destination/'FONT-LICENSE.txt')
    (destination/'START.txt').write_text('PRESTIGE TECH by Dominik Wasilak\n\nUruchom prestige-tech-dashboard.exe, aby otworzyć panel całego zestawu.\nKażdy inny plik EXE jest samodzielnym narzędziem z GUI.\nPython nie jest wymagany. Backend PowerShell 7, ADB, Nmap i środowiska Linux/Termux są potrzebne dla odpowiednich funkcji.\nDane i raporty: %LOCALAPPDATA%/PrestigeTech/<narzędzie>.\nWersje CLI: nazwa.exe --backend <argumenty>.\n',encoding='utf-8')
    sums=[hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name for path in sorted(destination.glob('*.exe'))]
    (destination/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
    archive=ROOT/'dist'/('prestige-tech-desktop-'+args.version+'-windows-x64.zip')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as bundle:
        for path in destination.iterdir():
            if path.is_file():bundle.write(path,path.name)
    print('ZIP: '+str(archive),flush=True)

if __name__=='__main__':main()
