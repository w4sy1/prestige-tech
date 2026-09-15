"""Exercise recovery states in real EXEs using only temporary fixture files."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'dist/desktop-0.3.2'
checks=[]
with tempfile.TemporaryDirectory(prefix='prestige-recovery-') as temporary:
    root=Path(temporary);environment=dict(os.environ,LOCALAPPDATA=str(root/'local'))
    def run(tool,*arguments,expected=0):
        process=subprocess.run([str(DIRECTORY/(tool+'.exe')),'--backend',*map(str,arguments)],cwd=root,
            env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        assert process.returncode==expected,process.stdout+process.stderr
        return json.loads(process.stdout)
    source=root/'source';source.mkdir();file=source/'file.txt';file.write_text('fixture')
    backup=root/'backup'
    run('prestige-backup','backup','--source',source,'--destination',backup,'--apply')
    result=run('prestige-backup','restore','--destination',backup,'--restore-to',root/'restored','--apply')
    state=json.loads(Path(result['data']['journal']).read_text(encoding='utf-8'))
    assert state['status']=='COMPLETE' and state['copied']==1
    checks.append('real EXE restore journal COMPLETE and verified file')
    manifest=backup/'manifest.json';record=json.loads(manifest.read_text());record['errors']=[{'error':'fixture'}]
    manifest.write_text(json.dumps(record))
    result=run('prestige-backup','verify','--destination',backup,expected=2)
    assert result['data']['ok'] is False
    checks.append('manifest errors cannot be overridden by complete=true')
    baseline=root/'baseline.json'
    baseline.write_text(json.dumps({'schema_version':1,'root':str(source.resolve()),'options':{'extended':True},
        'files':{'file.txt':{'size':file.stat().st_size,'mtime_ns':file.stat().st_mtime_ns,
        'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'extended':{'acl_status':'UNKNOWN','ads_status':'UNKNOWN'}}}}))
    result=run('prestige-integrity-monitor','check','--root',source,'--baseline',baseline,expected=2)
    assert result['data']['INCOMPLETE']==['file.txt']
    checks.append('unknown baseline ACL/ADS never verifies successfully')
    interrupted=root/'interrupted'
    for index in range(500):(source/('fixture-'+str(index)+'.txt')).write_bytes(b'x'*1024)
    process=subprocess.Popen([str(DIRECTORY/'prestige-backup.exe'),'--backend','backup','--source',str(source),
        '--destination',str(interrupted),'--apply'],cwd=root,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+30
        while not (interrupted/'manifest.json').exists() and time.monotonic()<deadline and process.poll() is None:
            time.sleep(.005)
        assert (interrupted/'manifest.json').exists(),'No initial checkpoint'
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
            process.wait(timeout=10)
    state=json.loads((interrupted/'manifest.json').read_text(encoding='utf-8'))
    assert state['complete'] is False,'Fixture backup finished before interruption'
    result=run('prestige-backup','verify','--destination',interrupted,expected=2)
    assert result['data']['ok'] is False
    checks.append('forcibly interrupted fixture backup retains valid incomplete manifest')
report={'version':'0.3.2','passed':True,'checks':checks}
(ROOT/'development/recovery-frozen-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
