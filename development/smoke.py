"""Real local integration tests. No Internet requests or system changes."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import venv

ROOT=Path(__file__).resolve().parents[1]

def invoke(command,expected=0):
    result=subprocess.run([str(c) for c in command],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
    if result.returncode!=expected:raise RuntimeError(f'Unexpected exit {result.returncode}, expected {expected}: {result.stderr[-2000:]}')
    return result.stdout

def main():
    wheel=next((ROOT/'prestige-tech-cli/reports/wheels').glob('*.whl'))
    checks=[]
    with tempfile.TemporaryDirectory(prefix='prestige-integration-') as temp:
        temp=Path(temp);environment=temp/'venv';venv.EnvBuilder(with_pip=True).create(environment)
        binary=environment/('Scripts' if os.name=='nt' else 'bin')
        python=binary/('python.exe' if os.name=='nt' else 'python')
        invoke([python,'-m','pip','install','--no-index','--no-deps',wheel]);checks.append('wheel installation in isolated venv')
        cli=binary/('prestige.exe' if os.name=='nt' else 'prestige')
        base=[cli,'--tools-root',ROOT]
        listing=invoke(base+['--list'])
        if listing.count('dostępne')!=24:raise RuntimeError('Incomplete launcher registry')
        checks.append('24 tools available via installed console command')
        data=temp/'data';data.mkdir();(data/'sample.txt').write_text('abc',encoding='utf-8')
        manifest=temp/'manifest.json'
        invoke(base+['prestige-hash-checker','generate','--root',data,'--manifest',manifest])
        invoke(base+['prestige-hash-checker','verify','--root',data,'--manifest',manifest]);checks.append('manifest generation and verification through CLI')
        (data/'sample.txt').write_text('changed',encoding='utf-8')
        invoke(base+['prestige-hash-checker','verify','--root',data,'--manifest',manifest],expected=2);checks.append('verification failure exit code preserved by CLI')
        metrics=temp/'metrics.json';metrics.write_text(json.dumps({'disk_free_percent':4,'packet_loss':8,'defender_enabled':True,'critical_errors':3}))
        analysis=json.loads(invoke(base+['ai','--input',metrics]))
        if len(analysis['data']['alerts'])!=3:raise RuntimeError('AI rule engine integration failed')
        checks.append('local diagnostic normalization and three expected alerts')
        backup=temp/'backup'
        invoke(base+['backup','backup','--source',data,'--destination',backup,'--apply'])
        invoke(base+['backup','verify','--destination',backup]);checks.append('backup and SHA256 verification on synthetic files')
        restored=temp/'restored'
        invoke(base+['backup','restore','--destination',backup,'--restore-to',restored,'--apply'])
        if (restored/'1-data/sample.txt').read_text(encoding='utf-8')!='changed':raise RuntimeError('Restored content mismatch')
        checks.append('verified backup restore through installed CLI')
        invoke(base+['prestige-hash-checker','compare-folders','--root',data,'--other',restored/'1-data'])
        checks.append('direct folder comparison through installed CLI')
    result={'passed':True,'checks':checks}
    (ROOT/'development/integration.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
