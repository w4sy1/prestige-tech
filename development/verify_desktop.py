"""Exercise every GUI, and run actual file hashing through a graphical form."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    results=[]
    for project in sorted(ROOT.glob('prestige-*')):
        if not (project/'gui.py').exists():continue
        for mode in ('--schema','--smoke'):
            result=subprocess.run([sys.executable,'gui.py',mode],cwd=project,capture_output=True,text=True,encoding='utf-8',timeout=30)
            if result.returncode:raise RuntimeError(project.name+' '+mode+' '+result.stderr[-1500:])
        results.append(project.name);print(project.name+': GUI OK',flush=True)
    code=r'''
from pathlib import Path
import tempfile,time,tkinter as tk,hashlib
from gui import Window
with tempfile.TemporaryDirectory() as temporary:
    file=Path(temporary)/'plik z odstępami.txt';file.write_text('fixture',encoding='utf-8')
    root=tk.Tk();root.withdraw();window=Window(root)
    window.variables['command'].set('file');window.variables['file'].set(str(file))
    class Tabs:
        def select(self,*args):pass
    window.run(Tabs(),None)
    deadline=time.monotonic()+15
    while window.process is not None and time.monotonic()<deadline:root.update();time.sleep(.05)
    assert window.process is None,'GUI backend timeout'
    assert hashlib.sha256(b'fixture').hexdigest() in window.last_output,window.last_output
    root.destroy()
print('Real GUI -> backend -> SHA256 result: PASS')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT/'prestige-hash-checker',capture_output=True,text=True,encoding='utf-8',timeout=30)
    if result.returncode:raise RuntimeError(result.stderr[-1500:])
    print(result.stdout)
    (ROOT/'development/desktop-verification.json').write_text(json.dumps({'passed':True,'gui_projects':len(results),'checks':['schema and window construction for every program','real graphical form executes hashing and displays correct SHA256']},indent=2),encoding='utf-8')

if __name__=='__main__':main()
