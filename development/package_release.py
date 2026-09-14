"""Create and verify a source ZIP from committed files, excluding private runtime data."""
from pathlib import Path
import hashlib
import json
import zipfile
import argparse
import re
from checkpoint import git

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',default='0.2.0');args=parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+',args.version):raise ValueError('Wersja musi mieć format X.Y.Z.')
    verification=json.loads((ROOT/'development/verification.json').read_text())
    if not verification['passed']:raise RuntimeError('Tests have not passed.')
    destination=ROOT/'dist';destination.mkdir(exist_ok=True)
    archive=destination/f'prestige-tech-{args.version}.zip'
    if archive.exists():raise FileExistsError(archive)
    entries=[]
    for project in sorted(ROOT.glob('prestige-*')):
        if not (project/'.git').exists():continue
        if git(project,'status','--porcelain').stdout.strip():raise RuntimeError(f'Uncommitted changes in {project.name}')
        for relative in git(project,'ls-files','-z').stdout.split('\0'):
            if not relative:continue
            path=project/relative
            if path.is_symlink():raise RuntimeError('No symlinks in release')
            if any(part in ('.git','__pycache__') or part.startswith('.env') for part in Path(relative).parts):raise RuntimeError('Unexpected private file')
            if Path(relative).parts[0] in ('logs','reports') and Path(relative).name!='.gitkeep':raise RuntimeError('Private runtime data staged')
            entries.append((path,f'{project.name}/{relative}'))
        version=json.loads((project/'metadata.json').read_text(encoding='utf-8'))['version']
        if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Nieprawidłowa wersja projektu.')
        if not git(project,'tag','--list','v'+version).stdout.strip():git(project,'tag','v'+version)
    for name in ('README.md','LICENSE','PROJECT-STATUS.md','SPECIFICATION.txt'):
        entries.append((ROOT/name,name))
    for path in sorted((ROOT/'development').glob('*')):
        if path.is_file():entries.append((path,'development/'+path.name))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for path,name in entries:z.write(path,name)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise RuntimeError('Corrupt ZIP')
        for project in verification['results']:
            actual=z.read(project['project']+'/LICENSE').decode('utf-8').replace('\r\n','\n')
            if actual!=(ROOT/'LICENSE').read_text(encoding='utf-8'):raise RuntimeError('MIT mismatch')
    value=hashlib.sha256(archive.read_bytes()).hexdigest()
    sums=[hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name for path in sorted(destination.glob('prestige-tech-*.zip'))]
    (destination/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
    print(json.dumps({'archive':str(archive),'files':len(entries),'bytes':archive.stat().st_size,'sha256':value}))

if __name__=='__main__':main()
