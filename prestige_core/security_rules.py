"""Evidence-based rules for every collected category; no malware verdicts."""
import ipaddress

CHECK_NAMES=('defender','firewall','updates','secure_boot','tpm','bitlocker','uac','smartscreen','rdp','smb','execution_policy','services','startup','tasks','proxy','hosts','dns','ports','connections','detections','processes')
WEIGHTS={'INFORMACYJNE':0,'NISKIE':1,'ŚREDNIE':5,'WYSOKIE':15,'KRYTYCZNE':30}
ESSENTIAL={'defender','firewall','updates','secure_boot','tpm','bitlocker','uac','rdp','smb','proxy'}

def user_location(value):
    value=str(value or '').lower().replace('/','\\')
    return any(part in value for part in ('\\temp\\','\\appdata\\','\\programdata\\'))

def audit(checks):
    if not isinstance(checks,dict):raise ValueError('Wymagany obiekt kontroli.')
    alerts=[];coverage={}
    def add(check,risk,detected,why,next_step,evidence=None):
        alerts.append(dict(check=check,risk=risk,detected=detected,why=why,what_to_check=next_step,evidence=evidence))
    def unknown(name):
        coverage[name]='UNKNOWN'
        add(name,'INFORMACYJNE','Brak wiarygodnego odczytu','Brak danych nie oznacza bezpiecznej konfiguracji.','Sprawdź uprawnienia i dostępność komponentu.')
    for name in CHECK_NAMES:
        record=checks.get(name,{})
        if not isinstance(record,dict) or record.get('status')!='OK':unknown(name);continue
        rows=record.get('data')
        if not isinstance(rows,list):raise ValueError('Dane kontroli muszą być tablicą.')
        if not rows and name in ESSENTIAL:unknown(name);continue
        coverage[name]='EVALUATED'
        for row in rows:
            if name=='hosts':
                if not isinstance(row,str):raise ValueError('Wpis hosts musi być tekstem.')
                parts=row.split('#',1)[0].split()
                if len(parts)>=2:
                    try:ipaddress.ip_address(parts[0])
                    except ValueError:
                        add(name,'NISKIE','Niepoprawny wpis hosts','Niepoprawna składnia utrudnia diagnostykę.','Sprawdź plik hosts ręcznie.');continue
                    hosts=[h.lower() for h in parts[1:] if h.lower() not in ('localhost','localhost.localdomain','ip6-localhost','ip6-loopback')]
                    if hosts:add(name,'NISKIE','Niestandardowe mapowania hosts','Mogą być legalnym adblockiem lub konfiguracją deweloperską.','Sprawdź przeznaczenie mapowań i źródło zmiany.',{'address':parts[0],'hosts':hosts})
                continue
            if not isinstance(row,dict):raise ValueError('Wpis kontroli musi być obiektem.')
            if name=='defender':
                if row.get('AntivirusEnabled') is False or row.get('RealTimeProtectionEnabled') is False:
                    add(name,'WYSOKIE','Ochrona Defender nieaktywna','Może brakować ochrony w czasie rzeczywistym.','Sprawdź, czy działa inny zaufany antywirus.')
                elif any(type(row.get(k)) is not bool for k in ('AntivirusEnabled','RealTimeProtectionEnabled')):unknown(name)
            elif name=='firewall':
                if row.get('Enabled') in (False,0):add(name,'WYSOKIE','Wyłączony profil zapory','Ruch może nie być filtrowany zgodnie z oczekiwaniami.','Sprawdź profil sieci i zasady zapory.',row.get('Name'))
                elif row.get('Enabled') not in (True,1):unknown(name)
            elif name=='updates':
                if str(row.get('StartType')) in ('Disabled','4'):add(name,'WYSOKIE','Usługa Windows Update wyłączona','Wyłączony start może uniemożliwiać aktualizacje.','Sprawdź zarządzanie aktualizacjami i polityki organizacji.')
                elif 'StartType' not in row:unknown(name)
            elif name=='secure_boot':
                if row.get('Enabled') is False:add(name,'ŚREDNIE','Secure Boot wyłączone','Brak tej warstwy kontroli rozruchu.','Sprawdź firmware i zgodność konfiguracji.')
                elif row.get('Enabled') is not True:unknown(name)
            elif name=='tpm':
                if row.get('TpmPresent') is False:add(name,'NISKIE','TPM nieobecny','Sprzętowa ochrona kluczy może być niedostępna.','Sprawdź możliwości sprzętu i firmware.')
                elif row.get('TpmReady') is False:add(name,'ŚREDNIE','TPM niegotowy','Funkcje zależne od TPM mogą nie działać.','Sprawdź stan TPM; nie czyść go bez zabezpieczenia kluczy odzyskiwania.')
                elif type(row.get('TpmPresent')) is not bool or type(row.get('TpmReady')) is not bool:unknown(name)
            elif name=='bitlocker':
                if str(row.get('ProtectionStatus')) in ('Off','0'):add(name,'ŚREDNIE','Ochrona BitLocker nieaktywna','Dane tego woluminu mogą nie mieć aktywnej ochrony BitLocker.','Sprawdź stan szyfrowania i czy ochrona została tymczasowo zawieszona.',row.get('MountPoint'))
                elif str(row.get('ProtectionStatus')) not in ('On','1'):unknown(name)
            elif name=='uac':
                if row.get('EnableLUA')==0:add(name,'WYSOKIE','UAC wyłączone','Zmniejsza kontrolę podnoszenia uprawnień.','Sprawdź politykę UAC i powód zmiany.')
                elif row.get('EnableLUA')!=1:unknown(name)
            elif name=='smartscreen':
                if str(row.get('SmartScreenEnabled','')).lower()=='off':add(name,'ŚREDNIE','Wpis SmartScreen ustawiony na Off','Może wyłączać tę warstwę ochrony.','Zweryfikuj skuteczne ustawienia i polityki Windows Security.')
                elif row.get('SmartScreenEnabled') is None:add(name,'INFORMACYJNE','Brak jawnego wpisu SmartScreen','Domyślne ustawienia lub polityki mogą określać działanie.','Sprawdź Windows Security; brak wpisu nie oznacza wyłączenia.')
            elif name=='rdp':
                if row.get('fDenyTSConnections')==0:add(name,'ŚREDNIE','RDP włączone','Zdalny dostęp wymaga kontroli ekspozycji.','Sprawdź NLA, zaporę i uprawnionych użytkowników.')
                elif row.get('fDenyTSConnections')!=1:unknown(name)
            elif name=='smb':
                if row.get('EnableSMB1Protocol') is True:add(name,'WYSOKIE','SMBv1 włączone','Przestarzały protokół zwiększa ryzyko.','Sprawdź zależności starszych urządzeń.')
                if row.get('RequireSecuritySignature') is False:add(name,'NISKIE','Podpisy SMB nie są wymagane','Może być zgodne z polityką, ale ogranicza integralność sesji.','Sprawdź wymagania podpisywania SMB w tej sieci.')
                if 'EnableSMB1Protocol' not in row:unknown(name)
            elif name=='execution_policy':
                if str(row.get('ExecutionPolicy')) in ('Bypass','Unrestricted'):add(name,'INFORMACYJNE','Liberalna execution policy','Execution Policy nie jest granicą bezpieczeństwa ani dowodem kompromitacji.','Sprawdź uzasadnienie konfiguracji w danym zakresie.',row.get('Scope'))
            elif name in ('services','startup','tasks'):
                paths=row.get('Executables',[row.get('ExecutablePath')])
                if not isinstance(paths,list):raise ValueError('Lista ścieżek wymagana.')
                for path in paths:
                    if user_location(path):add(name,'NISKIE','Automatyczne uruchamianie z lokalizacji użytkownika','Tak działają również legalne aplikacje; potrzebny jest kontekst.','Zweryfikuj pochodzenie pliku, podpis, właściciela i potrzebę autostartu.',{'name':row.get('Name',row.get('TaskName')),'path':path})
            elif name=='proxy':
                if row.get('ProxyEnable') in (True,1):add(name,'INFORMACYJNE','Skonfigurowane proxy użytkownika','Proxy może być wymagane w organizacji lub zmieniać trasę ruchu.','Zweryfikuj konfigurację proxy i kto ją ustawił.')
                elif row.get('ProxyEnable') not in (False,0):unknown(name)
            elif name=='dns':
                addresses=row.get('ServerAddresses',[])
                if not isinstance(addresses,list):raise ValueError('Lista DNS wymagana.')
                for address in addresses:
                    try:ip=ipaddress.ip_address(address)
                    except ValueError:add(name,'ŚREDNIE','Nieprawidłowy adres DNS','Resolver może być niedostępny.','Sprawdź konfigurację interfejsu.');continue
                    if ip.is_unspecified or ip.is_multicast:add(name,'ŚREDNIE','Nieużyteczny adres resolvera DNS','Adres nie wskazuje zwykłego serwera DNS.','Sprawdź konfigurację interfejsu.',address)
                    elif ip.is_loopback:add(name,'INFORMACYJNE','Lokalny resolver DNS','Wymaga działającej lokalnej usługi.','Sprawdź, czy lokalny resolver jest zamierzony i aktywny.',address)
            elif name=='ports':
                if row.get('LocalAddress') in ('0.0.0.0','::') and row.get('LocalPort') in (22,3389,445,139,5985,5986):
                    add(name,'ŚREDNIE','Usługa administracyjna nasłuchuje na wszystkich interfejsach','Nie dowodzi to dostępności z Internetu; zapora i routing decydują o ekspozycji.','Sprawdź proces, zakres reguł zapory i potrzebę usługi.',{'port':row.get('LocalPort'),'pid':row.get('OwningProcess')})
            elif name=='connections':
                if row.get('RemotePort') in (3333,4444,5555,14444):add(name,'INFORMACYJNE','Połączenie wymagające kontekstu aplikacji','Te porty mają wiele legalnych zastosowań. Sam numer nie dowodzi malware.','Powiąż połączenie z PID i przeznaczeniem procesu.',{'pid':row.get('OwningProcess'),'port':row.get('RemotePort')})
            elif name=='detections':
                add(name,'WYSOKIE' if row.get('ActionSuccess') is False else 'INFORMACYJNE','Wpis w historii wykryć Defender','Historyczny wpis nie musi oznaczać aktywnego zagrożenia.','Sprawdź czas, status i historię ochrony w Windows Security.',{'threat_id':row.get('ThreatID'),'action_success':row.get('ActionSuccess')})
            elif name=='processes':
                if user_location(row.get('Path')):add(name,'NISKIE','Proces w lokalizacji użytkownika','To częste także w legalnych aplikacjach.','Zweryfikuj pochodzenie i przeznaczenie aplikacji.',{'pid':row.get('PID'),'path':row.get('Path')})
                if row.get('Signature')=='NotSigned':add(name,'INFORMACYJNE','Proces bez podpisu','Brak podpisu nie jest dowodem malware.','Sprawdź zaufanie do wydawcy pliku.',row.get('PID'))
                elif row.get('Signature') in ('HashMismatch','NotTrusted'):add(name,'ŚREDNIE','Problem z weryfikacją podpisu','Możliwa zmiana pliku albo problem z łańcuchem zaufania.','Sprawdź plik i certyfikat wydawcy.',row.get('PID'))
    severity={name:max([WEIGHTS[a['risk']] for a in alerts if a['check']==name],default=0) for name in CHECK_NAMES}
    alerts.sort(key=lambda a:WEIGHTS[a['risk']],reverse=True)
    unknown_count=sum(state=='UNKNOWN' for state in coverage.values())
    return dict(checks=checks,alerts=alerts[:200],alerts_total=len(alerts),alerts_truncated=len(alerts)>200,coverage=coverage,
                risk_score=min(100,sum(severity.values())),score_meaning='Suma najwyższych wag kategorii, nie prawdopodobieństwo infekcji. 0 nie gwarantuje bezpieczeństwa.',unknown_checks=unknown_count,ok=not unknown_count)
