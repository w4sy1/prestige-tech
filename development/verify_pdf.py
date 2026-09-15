"""Check pagination, Unicode, long fields and refusal to replace an existing PDF."""
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'prestige-repair-report'))
from pdf_export import export_pdf
from pypdf import PdfReader

with tempfile.TemporaryDirectory(prefix='prestige-pdf-') as temporary:
    destination = Path(temporary) / 'multiple-pages.pdf'
    rows = [{'numer': number, 'opis': 'Zażółć gęślą jaźń. ' * 25,
             'identyfikator': 'a' * 400} for number in range(30)]
    export_pdf({'wiersze': rows, 'koniec': 'OSTATNI ZNACZNIK'}, destination)
    reader = PdfReader(destination)
    assert len(reader.pages) > 3
    text = '\n'.join(page.extract_text() for page in reader.pages)
    assert 'Zażółć gęślą jaźń' in text
    assert 'OSTATNI ZNACZNIK' in text
    original = destination.read_bytes()
    try:
        export_pdf({'overwrite': True}, destination)
    except FileExistsError:
        pass
    else:
        raise AssertionError('PDF overwrite was not rejected')
    assert destination.read_bytes() == original
    result = {'passed': True, 'pages': len(reader.pages),
              'checks': ['Unicode extraction', 'long fields and pagination', 'last row retained', 'existing file preserved']}
    (ROOT / 'development/pdf-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
