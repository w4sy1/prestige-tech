"""Install standalone Windows build recipes and CI without shared runtime imports."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = '''"""Build this repository's standalone GUI executable on Windows."""
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parent
if os.name != 'nt':
    raise SystemExit('Windows EXE must be built on Windows.')
command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile',
           '--console', '--name', root.name, '--hidden-import', 'pdf_export',
           '--collect-all', 'reportlab']
for name in ('metadata.json', 'LICENSE', 'THIRD_PARTY_NOTICES.txt', 'config', 'assets'):
    destination = name if (root / name).is_dir() else '.'
    command += ['--add-data', str(root / name) + ';' + destination]
if (root / 'app.py').exists():
    command += ['--hidden-import', 'app']
if (root / 'prestige.ps1').exists():
    command += ['--add-data', 'prestige.ps1;.', '--add-data', 'src;src']
if (root / 'prestige_cli').exists():
    command += ['--add-data', 'prestige_cli/author.json;prestige_cli']
command.append('gui.py')
subprocess.run(command, cwd=root, check=True)
executable = root / 'dist' / (root.name + '.exe')
for arguments in (['--schema'], ['--smoke']):
    subprocess.run([str(executable), *arguments], cwd=root, check=True, timeout=90)
print(executable)
'''
CI = '''name: Tests
on: [push, pull_request, workflow_dispatch]
permissions:
  contents: read
jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix:
        python: ['3.11', '3.14']
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python }}
      - name: Install optional dependencies
        shell: pwsh
        run: |
          python -m pip install -r requirements-gui.txt
          if (Test-Path requirements-signing.txt) { python -m pip install -r requirements-signing.txt }
      - name: Test backend and graphical window
        shell: pwsh
        run: |
          if (Test-Path app.py) {
            python -m unittest discover -s tests -v
            if ($LASTEXITCODE) { exit $LASTEXITCODE }
          } else {
            Get-ChildItem tests/*.ps1 | ForEach-Object {
              & pwsh -NoProfile -File $_.FullName
              if ($LASTEXITCODE) { exit $LASTEXITCODE }
            }
          }
          python gui.py --smoke
          exit $LASTEXITCODE
'''

for project in sorted(ROOT.glob('prestige-*')):
    if not (project / 'gui.py').exists():
        continue
    (project / 'build_exe.py').write_text(BUILD, encoding='utf-8')
    (project / 'requirements-build.txt').write_text(
        '-r requirements-gui.txt\npyinstaller==6.22.3\n' +
        ('-r requirements-signing.txt\n' if (project / 'requirements-signing.txt').exists() else ''),
        encoding='utf-8')
    workflow = project / '.github/workflows/tests.yml'
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(CI, encoding='utf-8')
    (project / 'docs/BUILD.md').write_text('''# Samodzielny EXE dla Windows

W katalogu tego repozytorium, z Pythonem 3.11 lub nowszym:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-build.txt
.venv/Scripts/python.exe build_exe.py
```

Wynik znajduje się w `dist/`. Interpreter Python i generator PDF są zawarte
w EXE. Zewnętrzne narzędzia systemowe potrzebne przez wybrane operacje
(np. PowerShell 7, ADB, Nmap) trzeba zainstalować oddzielnie.
Funkcje Termuxa wymagają Androida i Termuxa.

Program zapisuje dane w `%LOCALAPPDATA%/PrestigeTech/<nazwa-programu>`.
Przełącznik `--backend` uruchamia CLI. `--smoke` sprawdza konstrukcję okna.
Plik nie jest podpisany certyfikatem Authenticode.
Własny kod ma licencję MIT; licencje zależności znajdują się w
`THIRD_PARTY_NOTICES.txt` i `assets/FONT-LICENSE.txt`.

Workflow Tests uruchamia testy na Windows z Pythonem 3.11 i 3.14.
Dodanie konfiguracji nie oznacza wykonania jej na serwerze GitHub.
''', encoding='utf-8')
print('Installed standalone build recipes and CI for 26 repositories.')
