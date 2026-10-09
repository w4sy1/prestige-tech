"""Odczytowy audyt spowolnień bez wyłączania aktualizacji lub ochrony."""

import os

from .security_check import _powershell


SCRIPT = r'''
$r=[ordered]@{}
function probe($name,$block){try{$r[$name]=@{status='OK';data=@(&$block)}}catch{$r[$name]=@{status='UNKNOWN';data=@();error=$_.Exception.GetType().Name}}}
probe 'edge_processes' {Get-Process msedge -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,WorkingSet64}
probe 'startup' {Get-CimInstance Win32_StartupCommand | Select-Object Name,Location}
probe 'edge_policy' {$p=Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Edge' -ErrorAction SilentlyContinue;[pscustomobject]@{StartupBoostEnabled=$p.StartupBoostEnabled;BackgroundModeEnabled=$p.BackgroundModeEnabled}}
probe 'updates' {Get-Service wuauserv -ErrorAction Stop | Select-Object Name,Status,StartType}
probe 'defender' {Get-MpComputerStatus -ErrorAction Stop | Select-Object AntivirusEnabled,RealTimeProtectionEnabled}
probe 'drive' {Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$($env:SystemDrive)'" | Select-Object DeviceID,Size,FreeSpace}
$r | ConvertTo-Json -Depth 5
'''


def interpret(data):
    if not isinstance(data, dict):
        raise ValueError("Nieprawidłowy odczyt optymalizacji.")
    findings = []
    startup = data.get("startup", {})
    if startup.get("status") == "OK":
        count = len(startup.get("data") or [])
        findings.append({"area": "Autostart", "observation": f"{count} wpisów",
                         "action": "Przejrzyj aplikacje startowe w Ustawieniach Windows; wyłączaj tylko rozpoznane, niepotrzebne programy."})
    edge = data.get("edge_processes", {})
    if edge.get("status") == "OK" and edge.get("data"):
        findings.append({"area": "Microsoft Edge", "observation": f"{len(edge['data'])} procesów",
                         "action": "Jeśli nie używasz Edge w tle, sprawdź Startup Boost i aplikacje w tle w edge://settings/system. Nie usuwaj składników Windows."})
    edge_policy = data.get("edge_policy", {})
    if edge_policy.get("status") == "OK" and edge_policy.get("data"):
        row = edge_policy["data"][0]
        if row.get("StartupBoostEnabled") == 1 or row.get("BackgroundModeEnabled") == 1:
            findings.append({"area": "Polityka Edge", "observation": "Uruchamianie w tle wymuszone przez politykę",
                             "action": "Sprawdź administratora lub politykę organizacji; zwykłe ustawienie użytkownika może być zablokowane."})
    updates = data.get("updates", {})
    if updates.get("status") == "OK" and updates.get("data"):
        row = updates["data"][0]
        if str(row.get("StartType")) in ("Disabled", "4"):
            findings.append({"area": "Windows Update", "observation": "Usługa wyłączona",
                             "action": "Sprawdź polityki i przywróć aktualizacje; wyłączanie ich nie jest optymalizacją."})
    drive = data.get("drive", {})
    if drive.get("status") == "OK" and drive.get("data"):
        row = drive["data"][0]
        try:
            free_percent = 100 * int(row["FreeSpace"]) / int(row["Size"])
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            free_percent = None
        if free_percent is not None and free_percent < 10:
            findings.append({"area": "Miejsce na dysku", "observation": f"{free_percent:.1f}% wolnego",
                             "action": "Otwórz analizę PC Cleanup; najpierw obejrzyj plan, nie usuwaj dokumentów ani Pobranych automatycznie."})
    return {"schema_version": 1, "read_only": True, "sections": data,
            "findings": findings,
            "note": "Liczba procesów ani wpisów nie dowodzi spowolnienia. Program nie wyłącza telemetrii, aktualizacji, Defendera ani usług."}


def audit_windows(*, runner=None, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Audyt optymalizacji wymaga Windows.")
    data = _powershell(SCRIPT, runner=runner) if runner is not None else _powershell(SCRIPT)
    return interpret(data)
