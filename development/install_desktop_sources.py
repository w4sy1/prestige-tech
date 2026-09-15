"""Distribute standalone desktop adapters; no shared runtime dependency between projects."""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--font',required=True);args=parser.parse_args()
    for project in sorted(ROOT.glob('prestige-*')):
        if not (project/'metadata.json').exists():continue
        shutil.copy2(ROOT/'development/gui_template.py',project/'gui.py')
        shutil.copy2(ROOT/'development/pdf_template.py',project/'pdf_export.py')
        (project/'assets').mkdir(exist_ok=True)
        shutil.copy2(args.font,project/'assets/DejaVuSans.ttf')
        (project/'requirements-gui.txt').write_text('reportlab==5.0.1\n',encoding='utf-8')
        (project/'docs/GUI.md').write_text('# Interfejs graficzny\n\nUruchom `python gui.py`. Najpierw zainstaluj `requirements-gui.txt`, jeśli chcesz eksport PDF.\nFormularz udostępnia parametry programu. Operacje zapisujące wymagają zaznaczenia odpowiedniej opcji wykonania.\nZewnętrzne backendy (PowerShell, ADB, Nmap, Termux) pozostają wymagane dla odpowiednich funkcji.\nPrzycisk PDF eksportuje wynik; `python pdf_export.py --input raport.json --pdf raport.pdf` tworzy raport z JSON.\nWydanie EXE zawiera interpreter i biblioteki Python, ale nie zastępuje systemów Android/Termux.\n',encoding='utf-8')
        print(project.name)

if __name__=='__main__':main()
