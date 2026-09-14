"""Create one independent Python project; never a runtime dependency of tools."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def create(slug, title, description):
    target = ROOT / slug
    if target.exists():
        raise FileExistsError(target)
    for folder in ('config', 'logs', 'reports', 'tests', 'docs'):
        (target / folder).mkdir(parents=True, exist_ok=True)
    (target / 'LICENSE').write_text((ROOT/'prestige-windows-toolkit/LICENSE').read_text(), encoding='utf-8')
    (target/'config/author.json').write_text((ROOT/'prestige-windows-toolkit/config/author.json').read_text(), encoding='utf-8')
    (target/'runtime.py').write_text((ROOT/'development/runtime_template.py').read_text(), encoding='utf-8')
    (target/'metadata.json').write_text(json.dumps(dict(name=title, version='0.1.0'), ensure_ascii=False), encoding='utf-8')
    (target/'requirements.txt').write_text('# Python 3.11+, wyłącznie biblioteka standardowa.\n', encoding='utf-8')
    (target/'.gitignore').write_text('__pycache__/\n*.pyc\n.env\nlogs/*\n!logs/.gitkeep\nreports/*\n!reports/.gitkeep\n', encoding='utf-8')
    for folder in ('logs','reports'):
        (target/folder/'.gitkeep').touch()
    (target/'CHANGELOG.md').write_text('# Historia zmian\n\n## 0.1.0\n\n- Pierwsza samodzielna wersja CLI.\n', encoding='utf-8')
    (target/'SECURITY.md').write_text('# Bezpieczeństwo\n\nZgłoszenia: prestigetech@gmail.com. Nie dołączaj sekretów ani pełnych raportów publicznie. Dane domyślnie pozostają lokalne. Raporty mogą zawierać dane prywatne. Nie traktuj heurystyk jako dowodu malware.\n', encoding='utf-8')
    (target/'CONTRIBUTING.md').write_text('# Współpraca\n\nPython 3.11+. Testy: `python -m unittest discover -s tests -v`. Testuj na danych syntetycznych i mockach. Bez sekretów, shell=True i automatycznego podnoszenia uprawnień.\n', encoding='utf-8')
    (target/'docs/ARCHITECTURE.md').write_text('# Architektura\n\n`app.py`: CLI i logika domenowa. `runtime.py`: lokalne I/O, raporty, logowanie, backendy. `config/`: autor. `tests/`: unittest. `reports/`, `logs/`: lokalne wyniki. Projekt działa po skopiowaniu samodzielnego katalogu; nie importuje sąsiadujących projektów.\n\nZależności: Python 3.11+ i backendy wskazane w README. Brak pip dependencies.\n', encoding='utf-8')
    (target/'README.md').write_text(f'''# {title}
PRESTIGE TECH — by Dominik Wasilak — v0.1.0

{description}

## Instalacja i uruchomienie
Python 3.11+. Skopiuj katalog projektu. Bez instalowania pakietów pip.
```text
python app.py --help
python app.py --support
python -m unittest discover -s tests -v
```
Szczegóły i przykłady: `docs/USAGE.md`. Zależności systemowe opisano w tym pliku.

## Raporty i logi
Opcja `--output` zapisuje lokalnie JSON, TXT i HTML. Bez niej JSON trafia na stdout.
Log JSONL w `logs/` zawiera czas, moduł, akcję, wynik i typ błędu, bez treści wyjątków.
Kod 1 oznacza błąd, kod 2 oznacza negatywny wynik weryfikacji lub niekompletne dane,
jeżeli dane polecenie zwraca takie rozstrzygnięcie. `--dry-run` pokazuje plan bez wykonania.

## Bezpieczeństwo i ograniczenia
Narzędzie przeznaczone do celów edukacyjnych, diagnostycznych oraz do pracy z systemami i sieciami, których właścicielem jest użytkownik lub na których testowanie posiada zgodę.
Dane pozostają lokalne. Polecenia sieciowe wymagają świadomego wywołania;
zapytania DNS i połączenia do wskazanych hostów ujawniają im adres klienta.
Brak uprawnień lub backendu jest błędem, nie pozytywnym wynikiem audytu.
Zakres MVP i ograniczenia platformowe opisano w `docs/USAGE.md`.

## Autor i licencja
Dominik Wasilak, Prestige Tech, prestigetech@gmail.com. Licencja MIT: `LICENSE`.

## Wesprzyj autora
Opcja wsparcia autora zostanie udostępniona w przyszłości.
Linki w `config/author.json`.
''', encoding='utf-8')
    (target/'tests/test_runtime.py').write_text((ROOT/'development/runtime_tests.py').read_text(), encoding='utf-8')
    subprocess.run(['git','init',str(target)], check=True, capture_output=True)
    return target

if __name__ == '__main__':
    create(*sys.argv[1:])
