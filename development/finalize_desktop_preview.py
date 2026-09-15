"""Finalize an unpublished desktop preview after targeted rebuilds."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import uuid
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.3.1'
directory=ROOT/'dist'/('desktop-'+VERSION)
manifest=ROOT/'development/desktop-build.json'
report=json.loads(manifest.read_text(encoding='utf-8'))
assert report['version']==VERSION and len(report['results'])==26
replacement=json.loads((ROOT/'development/cli-rebuild.json').read_text(encoding='utf-8'))
report['results']=[replacement if row['project']==replacement['project'] else row for row in report['results']]
for row in report['results']:
    assert row['passed']
    path=directory/(row['project']+'.exe')
    with path.open('rb') as source:actual=hashlib.file_digest(source,'sha256').hexdigest()
    assert actual==row['sha256'],row['project']
help_result=subprocess.run([str(directory/'prestige-tech-cli.exe'),'--backend','--help'],capture_output=True,text=True,encoding='utf-8',timeout=90)
assert help_result.returncode==0 and 'v'+VERSION in help_result.stdout
manifest.write_text(json.dumps(report,indent=2),encoding='utf-8')
(directory/'SHA256SUMS.txt').write_text(''.join(row['sha256']+'  '+row['project']+'.exe\n' for row in report['results']),encoding='utf-8')
archive=ROOT/'dist'/('prestige-tech-desktop-'+VERSION+'-windows-x64.zip')
temporary=archive.with_name(archive.name+'.'+uuid.uuid4().hex+'.tmp')
with zipfile.ZipFile(temporary,'x',zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(directory.iterdir()):
        if path.is_file():bundle.write(path,path.name)
with zipfile.ZipFile(temporary) as bundle:assert bundle.testzip() is None
os.replace(temporary,archive)
print('Finalized '+str(archive))
