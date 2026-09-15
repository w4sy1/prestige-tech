"""Exercise packaged dependencies and hub discovery with temporary fixtures."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import argparse

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',default='0.3.1');args=parser.parse_args()
    DIRECTORY = ROOT / ('dist/desktop-'+args.version)
    executable = DIRECTORY / 'prestige-hash-checker.exe'
    checks = []
    with tempfile.TemporaryDirectory(prefix='prestige-exe-') as temporary:
        folder = Path(temporary)
        environment = dict(os.environ, LOCALAPPDATA=str(folder / 'local'),
                           PRESTIGE_SIGNING_PASSWORD='synthetic-test-password-only')
        def run(*arguments, expected=0):
            process = subprocess.run([str(executable), '--backend', *map(str, arguments)],
                cwd=folder, env=environment, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=90)
            if process.returncode != expected:
                raise AssertionError(process.stdout + process.stderr)
            return process.stdout
        source = folder / 'dane z odstępami.txt'
        source.write_text('Zażółć gęślą jaźń', encoding='utf-8')
        pdf = folder / 'raport.pdf'
        output = run('file', '--file', source, '--pdf', pdf)
        assert hashlib.sha256(source.read_bytes()).hexdigest() in output
        from pypdf import PdfReader
        assert len(PdfReader(pdf).pages) >= 1
        checks.append('packaged SHA256 and Unicode PDF export')
        private = folder / 'private.pem'; public = folder / 'public.pem'
        signature = folder / 'signature.json'
        run('keygen', '--private-key', private, '--public-key', public)
        assert b'ENCRYPTED PRIVATE KEY' in private.read_bytes()
        run('sign', '--manifest', source, '--private-key', private, '--signature', signature)
        output = run('verify-signature', '--manifest', source, '--public-key', public, '--signature', signature)
        assert '"ok": true' in output
        source.write_text('changed', encoding='utf-8')
        output = run('verify-signature', '--manifest', source, '--public-key', public, '--signature', signature, expected=2)
        assert '"ok": false' in output
        checks.append('packaged encrypted Ed25519 keys, signatures and tamper rejection')
        executable=DIRECTORY/'prestige-lan-radar.exe'
        observation=folder/'hosts.json';database=folder/'hosts.sqlite'
        observation.write_text(json.dumps([{'mac':'02:00:00:00:00:01','ips':['192.168.1.2','192.168.1.20']}]))
        run('observe','--database',database,'--input',observation)
        observation.write_text(json.dumps([{'mac':'02:00:00:00:00:02','ip':'192.168.1.20'}]))
        assert 'POSSIBLE_MAC_CHANGE' in run('observe','--database',database,'--input',observation)
        checks.append('packaged LAN change detection on secondary address')
        executable=DIRECTORY/'prestige-malware-triage.exe'
        evidence=folder/'evidence.json'
        evidence.write_text(json.dumps({'processes':{'status':'OK','data':[{'pid':42,'signature':'NotSigned'}]},
            'gpu':{'status':'OK','data':[{'pid':42,'sample_count':16,'sample_seconds':30,'mean_percent':90,'high_fraction':1}]}}))
        assert 'Utrzymujące' in run('--input',evidence)
        checks.append('packaged sustained GPU rule on synthetic evidence')
        dashboard = DIRECTORY / 'prestige-tech-dashboard.exe'
        if dashboard.exists():
            process = subprocess.run([str(dashboard), '--backend', '--list'],
                cwd=folder, env=environment, capture_output=True, text=True,
                encoding='utf-8', timeout=90)
            assert process.returncode == 0, process.stderr
            assert '"available": false' not in process.stdout, process.stdout
            checks.append('packaged dashboard discovers adjacent tools from unrelated cwd')
    report = {'passed': True, 'version': args.version, 'checks': checks}
    (ROOT / 'development/frozen-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
