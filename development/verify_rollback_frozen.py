"""Check rollback refusal from real EXEs, strictly within temporary fixtures."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import time
import argparse

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--version',default='0.3.4');args=parser.parse_args()
DIRECTORY=ROOT/'dist'/('desktop-'+args.version)
checks=[]
with tempfile.TemporaryDirectory(prefix='prestige-rollback-') as temporary:
    root=Path(temporary);scratch=root/'temp';scratch.mkdir()
    env=dict(os.environ,LOCALAPPDATA=str(root/'local'),TEMP=str(scratch),TMP=str(scratch),TMPDIR=str(scratch))
    def run(tool,*args,expected=0):
        process=subprocess.run([str(DIRECTORY/(tool+'.exe')),'--backend',*map(str,args)],cwd=root,
            env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        assert process.returncode==expected,process.stdout+process.stderr
        return json.loads(process.stdout) if expected==0 else None
    rows=[]
    for name in ('a.txt','b.txt'):
        file=scratch/name;file.write_text(name);os.utime(file,(time.time()-10*86400,)*2)
        rows.append({'path':name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'clean_allowed':True})
    plan=root/'plan.json';plan.write_text(json.dumps({'schema_version':1,'root':str(scratch),'files':rows}))
    quarantine=root/'quarantine'
    run('prestige-pc-cleanup','clean','--plan',plan,'--quarantine',quarantine,'--apply')
    manifest=json.loads((quarantine/'manifest.json').read_text())
    (quarantine/manifest['files'][-1]['stored']).unlink()
    run('prestige-pc-cleanup','restore','--quarantine',quarantine,'--apply',expected=1)
    assert not (scratch/'a.txt').exists()
    assert (quarantine/manifest['files'][0]['stored']).is_file()
    checks.append('missing quarantine file refuses rollback before restoring any file')
    source=root/'prestige-fixture';source.mkdir()
    (source/'metadata.json').write_text(json.dumps({'version':'0.1.0'}));(source/'app.py').write_text('old fixture')
    result=run('prestige-usb-toolkit','prepare','--destination',root/'usb','--tool',source,'--apply')
    usb=Path(result['data']['root'])
    (source/'metadata.json').write_text(json.dumps({'version':'0.2.0'}));(source/'app.py').write_text('new fixture')
    result=run('prestige-usb-toolkit','update','--destination',usb,'--tool',source,'--apply')
    journal=Path(result['data']['rollback'])
    (journal/'prestige-fixture/app.py').write_text('corrupt saved fixture')
    run('prestige-usb-toolkit','rollback','--destination',journal,'--apply',expected=1)
    assert (usb/'Tools/prestige-fixture/app.py').read_text()=='new fixture'
    assert run('prestige-usb-toolkit','verify','--destination',usb)['data']['ok']
    checks.append('corrupt saved USB version is refused while installed version stays intact')
result={'version':args.version,'passed':True,'checks':checks}
(ROOT/'development/rollback-frozen-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
