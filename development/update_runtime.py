"""Maintenance operation: synchronize the already-tested local stdlib helpers."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
template=ROOT/'development/runtime_template.py'
text=template.read_text(encoding='utf-8')
if 'import sqlite3\n' not in text:text=text.replace('import shutil\n','import shutil\nimport sqlite3\n')
text=text.replace('except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.SubprocessError) as exc:',"except (KeyboardInterrupt,EOFError):\n        print('Przerwano.',file=sys.stderr)\n        return 130\n    except (OSError,ValueError,RuntimeError,KeyError,TypeError,sqlite3.Error,subprocess.SubprocessError) as exc:")
template.write_text(text,encoding='utf-8')
for project in ROOT.glob('prestige-*'):
    if (project/'runtime.py').exists():(project/'runtime.py').write_text(text,encoding='utf-8')
    ignore=project/'.gitignore'
    extra='\n*.sqlite\n*.sqlite-*\n*.db\n*.db-*\n*.egg-info/\nbuild/\ndist/\n'
    if ignore.exists() and '*.sqlite' not in ignore.read_text():ignore.write_text(ignore.read_text()+extra,encoding='utf-8')
