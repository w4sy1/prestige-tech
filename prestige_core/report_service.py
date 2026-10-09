from pathlib import Path
import datetime as dt
import html
import json
import math
import uuid

LABELS={'numer_zlecenia':'Numer zlecenia','klient':'Klient','urzadzenie':'Urządzenie','producent':'Producent','model':'Model','serial':'Numer seryjny (opcjonalny)',
 'data':'Data','zgloszony_problem':'Zgłoszony problem','diagnoza':'Diagnoza','wykonane_czynnosci':'Wykonane czynności','czesci':'Części','test_koncowy':'Test końcowy',
 'zalecenia':'Zalecenia','czas_pracy_min':'Czas pracy (minuty)','technik':'Technik',
 'status_weryfikacji':'Weryfikacja naprawy'}
REQUIRED=('numer_zlecenia','klient','urzadzenie','zgloszony_problem','diagnoza','wykonane_czynnosci','test_koncowy')

def missing_fields(data):
    return [LABELS[name] for name in REQUIRED if not isinstance(data.get(name),str) or not data[name].strip()]

def template():
    return {**{name:'' for name in LABELS},'data':dt.date.today().isoformat(),'technik':'Dominik Wasilak — Prestige Tech','czesci':[],'czas_pracy_min':0,
            'status_weryfikacji':'Niepotwierdzona — brak udokumentowanego testu po naprawie'}

def validate(data):
    if not isinstance(data,dict) or set(data)-set(LABELS):raise ValueError('Nieznane pola raportu.')
    result={**template(),**data}
    for name in REQUIRED:
        if not isinstance(result[name],str) or not result[name].strip():raise ValueError('Brakuje wymaganego pola.')
    for name in LABELS:
        if name not in ('czesci','czas_pracy_min') and (not isinstance(result[name],str) or len(result[name])>50000):raise ValueError('Nieprawidłowy tekst.')
    if result['status_weryfikacji'] not in (
            'Niepotwierdzona — brak udokumentowanego testu po naprawie',
            'Potwierdzona — test po naprawie wykonano i opisano'):
        raise ValueError('Nieprawidłowy status weryfikacji naprawy.')
    if result['status_weryfikacji'].startswith('Potwierdzona') and len(result['test_koncowy'].strip()) < 20:
        raise ValueError('Potwierdzenie wymaga opisu wykonanego testu końcowego (co najmniej 20 znaków).')
    dt.date.fromisoformat(result['data'])
    if not isinstance(result['czesci'],list) or any(not isinstance(x,str) for x in result['czesci']):raise ValueError('Części jako lista tekstów.')
    duration=result['czas_pracy_min']
    if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<0:raise ValueError('Nieprawidłowy czas pracy.')
    return result

def render(data,directory):
    data=validate(data);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);base=directory/('serwis-'+uuid.uuid4().hex)
    rows=[];text=['PRESTIGE TECH','by Dominik Wasilak','Raport serwisowy','']
    for key,label in LABELS.items():
        value='\n'.join(data[key]) if isinstance(data[key],list) else str(data[key])
        rows.append(f'<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>');text.extend([label+':',value,''])
    document='<!doctype html><html lang="pl"><meta charset="utf-8"><title>Raport serwisowy Prestige Tech</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:20px}table{border-collapse:collapse;width:100%}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #ddd;padding:12px;white-space:pre-wrap;overflow-wrap:anywhere}th{width:28%}@media print{body{margin:0}tr{break-inside:avoid}}</style><h1>PRESTIGE TECH</h1><p>by Dominik Wasilak</p><h2>Raport serwisowy</h2><h2>'+html.escape(data['status_weryfikacji'])+'</h2><table>'+''.join(rows)+'</table></html>'
    # UUID nadaje nazwę, a tryb x chroni również przed nieoczekiwaną kolizją.
    paths = [base.with_suffix('.'+extension) for extension in ('json','txt','html')]
    if any(path.exists() for path in paths):
        raise FileExistsError('Plik raportu już istnieje.')
    created=[]
    try:
        for path, content in zip(paths, (json.dumps(data,ensure_ascii=False,indent=2)+'\n',
                                         '\n'.join(text),document)):
            with path.open('x',encoding='utf-8') as stream:
                created.append(path)
                stream.write(content)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return {'files':[str(base.with_suffix('.'+extension)) for extension in ('html','json','txt')]}
