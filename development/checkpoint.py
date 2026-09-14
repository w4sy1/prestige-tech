"""Commit independent repositories, without publishing or global Git changes."""
from pathlib import Path
import json
import subprocess
import argparse
ROOT=Path(__file__).resolve().parents[1]

def git(project,*args,check=True):
    return subprocess.run(['git','-c',f'safe.directory={project.as_posix()}','-c','user.name=Dominik Wasilak','-c','user.email=prestigetech@gmail.com','-C',str(project),*args],check=check,capture_output=True,text=True,encoding='utf-8',errors='replace')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--message',default='feat: zaimplementowano i przetestowano MVP v0.1.0');args=parser.parse_args()
    verification=json.loads((ROOT/'development/verification.json').read_text())
    integration=json.loads((ROOT/'development/integration.json').read_text())
    if not verification['passed'] or not integration['passed']:raise RuntimeError('Tests must pass before checkpoint.')
    commits=[]
    for project in sorted(ROOT.glob('prestige-*')):
        if not (project/'.git').is_dir():continue
        if git(project,'rev-parse','--verify','HEAD',check=False).returncode:
            base=['LICENSE','README.md','CHANGELOG.md','SECURITY.md','CONTRIBUTING.md','.gitignore','config','logs/.gitkeep','reports/.gitkeep','metadata.json','requirements.txt','runtime.py','tests/test_runtime.py','docs/ARCHITECTURE.md']
            git(project,'add','--',*[f for f in base if (project/f).exists()])
            git(project,'commit','-m','chore: przygotowano samodzielny projekt na licencji MIT')
        git(project,'add','--all')
        if git(project,'diff','--cached','--quiet',check=False).returncode:
            git(project,'commit','-m',args.message)
        commits.append({'project':project.name,'commit':git(project,'rev-parse','HEAD').stdout.strip()})
    (ROOT/'development/commits.json').write_text(json.dumps(commits,indent=2),encoding='utf-8')
    print(f'Committed {len(commits)} independent projects.')

if __name__=='__main__':main()
