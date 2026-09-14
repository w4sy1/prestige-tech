"""Run isolated project test processes and inspect independent project structure."""
from pathlib import Path
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
REQUIRED=['README.md','LICENSE','CHANGELOG.md','SECURITY.md','CONTRIBUTING.md','config','logs','reports','tests','docs','metadata.json']

def main():
    results=[];failed=False
    for project in sorted(ROOT.glob('prestige-*')):
        if not project.is_dir():continue
        missing=[name for name in REQUIRED if not (project/name).exists()]
        if (project/'LICENSE').read_text(encoding='utf-8')!=(ROOT/'prestige-windows-toolkit/LICENSE').read_text(encoding='utf-8'):missing.append('MIT mismatch')
        if (project/'app.py').exists():
            command=[sys.executable,'-m','unittest','discover','-s','tests','-v']
            help_command=[sys.executable,'app.py','--help']
        else:
            command=['pwsh','-NoProfile','-Command','& ./tests/run.ps1; if ($LASTEXITCODE) {exit $LASTEXITCODE}; & ./tests/operations.ps1']
            help_command=['pwsh','-NoProfile','-File','prestige.ps1','-Command','modules']
        test=subprocess.run(command,cwd=project,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        output=test.stdout+test.stderr
        count_match=re.search(r'Ran (\d+) tests',output)
        count=int(count_match.group(1)) if count_match else sum(int(n) for n in re.findall(r'PASS: (\d+)',output))
        help_result=subprocess.run(help_command,cwd=project,capture_output=True,timeout=30)
        passed=not missing and test.returncode==0 and help_result.returncode==0
        results.append({'project':project.name,'passed':passed,'tests':count,'missing':missing})
        print(f'{project.name}: {"PASS" if passed else "FAIL"} ({count})',flush=True)
        if not passed:print(output);failed=True
    report={'projects':len(results),'tests':sum(r['tests'] for r in results),'passed':not failed,'results':results}
    (ROOT/'development/verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return int(failed)

if __name__=='__main__':raise SystemExit(main())
