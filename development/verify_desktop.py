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
import tempfile,time,tkinter as tk,hashlib,sys
from unittest.mock import patch
from gui import Window,MAX_OUTPUT,arguments
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
    with patch('gui.backend_command',return_value=[sys.executable,'-u','-c',"import sys;sys.stdout.buffer.write(('ą'*1200000+'KONIEC').encode('utf-8'))"]):
        window.run(Tabs(),None)
        deadline=time.monotonic()+30
        while window.process is not None and time.monotonic()<deadline:root.update();time.sleep(.01)
        assert window.process is None,'Output flood timeout'
        assert len(window.last_output)<=MAX_OUTPUT
        assert window.output_truncated
        assert window.last_output.endswith('KONIEC')
        assert '\ufffd' not in window.last_output,'Broken UTF-8 chunk decoding'
    with patch('gui.backend_command',return_value=[sys.executable,'-u','-c',"import time;print('READY',flush=True);time.sleep(60)"]):
        window.run(Tabs(),None)
        deadline=time.monotonic()+5
        while 'READY' not in window.last_output and time.monotonic()<deadline:root.update();time.sleep(.01)
        assert 'READY' in window.last_output
        assert window.stop()
        deadline=time.monotonic()+5
        while window.process is not None and time.monotonic()<deadline:root.update();time.sleep(.01)
        assert window.process is None,'Stopped backend still running'
    window.run(Tabs(),None)
    deadline=time.monotonic()+15
    while window.process is not None and time.monotonic()<deadline:root.update();time.sleep(.01)
    assert hashlib.sha256(b'fixture').hexdigest() in window.last_output,'Restart after stop failed'
    assert not window.output_truncated
    assert arguments([{'dest':'x','option':'--x','multiple':True,'append':False}],{'x':'a\nb'})==['--x','a','b']
    assert arguments([{'dest':'x','option':'--x','multiple':True,'append':True}],{'x':'a\nb'})==['--x','a','--x','b']
    root.destroy()
print('Real GUI -> backend -> SHA256 result: PASS')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT/'prestige-hash-checker',capture_output=True,text=True,encoding='utf-8',timeout=90)
    if result.returncode:raise RuntimeError(result.stderr[-1500:])
    print(result.stdout)
    (ROOT/'development/desktop-verification.json').write_text(json.dumps({'passed':True,'gui_projects':len(results),'checks':['schema and window construction for every program','real graphical form executes hashing and displays correct SHA256','bounded output flood and Unicode streaming','stop backend and restart operation','multiple argument construction']},indent=2),encoding='utf-8')

if __name__=='__main__':main()
