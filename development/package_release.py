"""Create and verify a source ZIP from committed files, excluding private runtime data."""
from pathlib import Path
import hashlib
import json
import zipfile
from checkpoint import git

ROOT=Path(__file__).resolve().parents[1]

def main():
    verification=json.loads((ROOT/'development/verification.json').read_text())
    if not verification['passed']:raise RuntimeError('Tests have not passed.')
    destination=ROOT/'dist';destination.mkdir(exist_ok=True)
    archive=destination/'prestige-tech-0.1.0.zip'
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
        if not git(project,'tag','--list','v0.1.0').stdout.strip():git(project,'tag','v0.1.0')
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
    (destination/'SHA256SUMS.txt').write_text(value+'  '+archive.name+'\n',encoding='utf-8')
    print(json.dumps({'archive':str(archive),'files':len(entries),'bytes':archive.stat().st_size,'sha256':value}))

if __name__=='__main__':main()
