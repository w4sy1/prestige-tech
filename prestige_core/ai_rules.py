def evaluate(metrics):
    alerts=[]
    def add(code,risk,evidence,reason,check):alerts.append({'code':code,'risk':risk,'evidence':evidence,'reason':reason,'what_to_check':check})
    disk=metrics.get('disk_free_percent')
    if disk is not None and disk<10:add('LOW_DISK','WYSOKIE' if disk<5 else 'ŚREDNIE',disk,'Mało wolnego miejsca może utrudniać aktualizacje i zapis.','Przejrzyj zajętość dysku i plan czyszczenia; nie usuwaj plików w ciemno.')
    loss=metrics.get('packet_loss')
    if loss is not None and loss>2:add('PACKET_LOSS','WYSOKIE' if loss>=10 else 'ŚREDNIE',loss,'Utrata odpowiedzi może oznaczać problem lub limitowanie ICMP.','Porównaj pomiary bramy, kilku hostów i połączenia kablowego.')
    if metrics.get('defender_enabled') is False:add('DEFENDER_DISABLED','WYSOKIE',False,'Defender nieaktywny; może działać inny antywirus.','Sprawdź rzeczywistego dostawcę ochrony i polityki.')
    if metrics.get('critical_errors',0)>0:add('SYSTEM_ERRORS','ŚREDNIE',metrics['critical_errors'],'Zarejestrowano błędy krytyczne.','Sprawdź czas, źródło i korelację z objawami w dzienniku Windows.')
    if metrics.get('jitter_ms',0)>30:add('NETWORK_JITTER','ŚREDNIE',metrics['jitter_ms'],'Zmienność opóźnień może pogarszać rozmowy i gry.','Porównaj bramę i host zewnętrzny; powtórz pomiar po kablu.')
    if metrics.get('battery_temperature_c',0)>=45:add('BATTERY_TEMPERATURE','ŚREDNIE',metrics['battery_temperature_c'],'Podwyższona temperatura baterii w momencie pomiaru.','Porównaj z warunkami pracy i zaleceniami producenta; ponów pomiar po ostygnięciu.')
    if metrics.get('storage_temperature_c',0)>=60:add('STORAGE_TEMPERATURE','ŚREDNIE',metrics['storage_temperature_c'],'Wysoka temperatura wskazana przez licznik dysku.','Sprawdź limit konkretnego modelu, chłodzenie i obciążenie.')
    unhealthy=[state for state in metrics.get('disk_health',[]) if state.lower() in ('unhealthy','warning','unhealthy/failed','nieprawidłowy')]
    if unhealthy:add('STORAGE_HEALTH','WYSOKIE',unhealthy,'System zgłasza ostrzeżenie stanu nośnika.','Zweryfikuj backup i szczegółową diagnostykę producenta; nie traktuj samego statusu jako diagnozy awarii.')
    if metrics.get('unknown_sections',0):add('INCOMPLETE_EVIDENCE','INFORMACYJNE',metrics['unknown_sections'],'Część modułów nie dostarczyła pełnych danych.','Sprawdź wymagane backendy/uprawnienia i ponów wskazane moduły.')
    for index,alert in enumerate(metrics.get('source_alerts',[])):
        add('SOURCE_'+str(index+1),alert['risk'],alert['detected'],'Wskazanie pochodzi z reguł raportu źródłowego; nie jest nowym potwierdzeniem.',alert['what_to_check'])
    return alerts

def score(alerts):
    weights={'INFORMACYJNE':0,'NISKIE':5,'ŚREDNIE':15,'WYSOKIE':30,'KRYTYCZNE':50}
    return min(100,sum(weights[a['risk']] for a in alerts))
