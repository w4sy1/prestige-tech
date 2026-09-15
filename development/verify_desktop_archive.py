"""Verify all packaged executables against build hashes, including ZIP integrity."""
from pathlib import Path
import hashlib
import json
import zipfile
import argparse

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--version',default='0.3.2');args=parser.parse_args()
archive = ROOT / ('dist/prestige-tech-desktop-'+args.version+'-windows-x64.zip')
build = json.loads((ROOT / 'development/desktop-build.json').read_text())
assert len(build['results']) == 26
assert build['version'] == args.version
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    names = {name for name in bundle.namelist() if name.endswith('.exe')}
    assert len(names) == 26
    for row in build['results']:
        assert row['passed']
        name = row['project'] + '.exe'
        assert name in names
        assert hashlib.sha256(bundle.read(name)).hexdigest() == row['sha256']
    for required in ('LICENSE', 'THIRD_PARTY_NOTICES.txt', 'FONT-LICENSE.txt', 'START.txt', 'SHA256SUMS.txt'):
        assert required in bundle.namelist()
with archive.open('rb') as source: digest = hashlib.file_digest(source, 'sha256').hexdigest()
result = {'passed': True, 'version': args.version, 'executables': 26, 'bytes': archive.stat().st_size, 'sha256': digest}
(ROOT / 'development/desktop-archive-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
with (archive.parent / 'SHA256SUMS.txt').open('w', encoding='utf-8') as stream:
    for path in sorted(archive.parent.glob('prestige-tech-*.zip')):
        with path.open('rb') as source:
            stream.write(hashlib.file_digest(source, 'sha256').hexdigest() + '  ' + path.name + '\n')
print(json.dumps(result, indent=2))
