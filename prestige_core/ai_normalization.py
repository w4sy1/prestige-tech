import math

def normalize(report):
    if not isinstance(report,dict):raise ValueError('Raport musi być obiektem JSON.')
    found={};values={'disk_free_percent':[],'packet_loss':[],'defender_enabled':[],'critical_errors':[],
        'jitter_ms':[],'battery_temperature_c':[],'storage_temperature_c':[],'cpu_percent':[]}
    source_alerts=[];unknown=[];health=[]
    def visit(value,depth=0):
        if depth>20:raise ValueError('Zbyt głęboki raport.')
        if isinstance(value,dict):
            if value.get('status') in ('UNKNOWN','UNAVAILABLE','ACCESS_DENIED','ERROR','PARTIAL'):
                unknown.append(str(value.get('module','sekcja'))[:100])
            if isinstance(value.get('HealthStatus'),str):health.append(value['HealthStatus'])
            if isinstance(value.get('alerts'),list):
                for alert in value['alerts']:
                    if isinstance(alert,dict) and alert.get('risk') in ('INFORMACYJNE','NISKIE','ŚREDNIE','WYSOKIE','KRYTYCZNE'):
                        source_alerts.append({'risk':alert['risk'],'detected':str(alert.get('detected',alert.get('title',alert.get('code','Alert źródłowy'))))[:500],
                            'what_to_check':str(alert.get('what_to_check','Sprawdź szczegóły w raporcie źródłowym.'))[:1000]})
            if (type(value.get('Size')) in (int,float) and type(value.get('FreeSpace')) in (int,float)
                    and value['Size']>0 and 0<=value['FreeSpace']<=value['Size']):
                values['disk_free_percent'].append(100*value['FreeSpace']/value['Size'])
            for key,item in value.items():
                canonical={'FreePercent':'disk_free_percent','AntivirusEnabled':'defender_enabled',
                    'packet_loss_percent':'packet_loss',
                    'temperature_c':'battery_temperature_c','Temperature':'storage_temperature_c'}.get(key,key)
                if canonical in values:
                    if canonical=='defender_enabled':
                        if type(item) is not bool and item is not None:raise ValueError('Defender wymaga bool.')
                    elif item is not None:
                        if type(item) not in (int,float) or not math.isfinite(item) or item<0:raise ValueError('Nieprawidłowa liczba.')
                        if canonical in ('disk_free_percent','packet_loss','cpu_percent') and item>100:raise ValueError('Procent poza zakresem.')
                        if canonical=='critical_errors' and item!=int(item):raise ValueError('Liczba błędów musi być całkowita.')
                    if item is not None:values[canonical].append(item)
                elif isinstance(item,(dict,list)):visit(item,depth+1)
        elif isinstance(value,list):
            for item in value:visit(item,depth+1)
    visit(report)
    for key,items in values.items():
        if items:found[key]=all(items) if key=='defender_enabled' else min(items) if key=='disk_free_percent' else max(items)
    if source_alerts:
        unique={(row['risk'],row['detected']):row for row in source_alerts}
        found['source_alerts']=list(unique.values())[:200]
    if unknown:found['unknown_sections']=len(unknown)
    if health:found['disk_health']=sorted(set(health))
    return found
