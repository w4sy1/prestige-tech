"""Odczytowa diagnostyka Windows Toolkit dla System Center."""

from datetime import datetime, timezone
import os

from .security_check import _powershell


QUERIES = {
    "update_history": """$s=New-Object -ComObject Microsoft.Update.Session;
        $u=$s.CreateUpdateSearcher();$n=[Math]::Min($u.GetTotalHistoryCount(),50);
        if($n -gt 0){$u.QueryHistory(0,$n) | Select-Object Title,Date,
            @{n='Operation';e={[int]$_.Operation}},@{n='ResultCode';e={[int]$_.ResultCode}},HResult}""",
    "update_services": """Get-Service -Name wuauserv,bits,usosvc -ErrorAction Stop |
        Select-Object Name,Status,StartType""",
    "update_policies": """foreach($p in @('HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU',
        'HKLM:\\SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings')){
        if(Test-Path -LiteralPath $p){Get-ItemProperty -LiteralPath $p |
            Select-Object @{n='Path';e={$p}},NoAutoUpdate,AUOptions,UseWUServer,
                PauseUpdatesExpiryTime,PauseFeatureUpdatesEndTime,PauseQualityUpdatesEndTime}}""",
    "reboot": """[pscustomobject]@{
        CBS=(Test-Path -LiteralPath 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\RebootPending');
        WindowsUpdate=(Test-Path -LiteralPath 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired');
        PendingRenameOperations=($null -ne (Get-ItemPropertyValue -LiteralPath 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager' -Name PendingFileRenameOperations -ErrorAction SilentlyContinue))}""",
}


def collect(*, runner=None, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Diagnostyka Windows Toolkit wymaga Windows.")
    parts = []
    for name, query in QUERIES.items():
        parts.append(
            f"try{{$d=@({query});$r['{name}']=@{{status='OK';data=$d}}}}"
            f"catch{{$r['{name}']=@{{status='UNKNOWN';data=@();error=$_.Exception.GetType().Name}}}}"
        )
    script = "$ErrorActionPreference='Stop';$r=[ordered]@{};" + ";".join(parts) + ";$r|ConvertTo-Json -Depth 6"
    options = {"runner": runner} if runner is not None else {}
    result = _powershell(script, 90, **options)
    if not isinstance(result, dict):
        raise RuntimeError("Nieprawidłowy wynik Windows Toolkit.")
    for name in QUERIES:
        section = result.get(name)
        if not isinstance(section, dict) or section.get("status") not in ("OK", "UNKNOWN"):
            raise RuntimeError("Brak sekcji diagnostycznej: " + name)
        if not isinstance(section.get("data"), list):
            raise RuntimeError("Nieprawidłowe dane sekcji: " + name)
    return {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
            "sections": result, "note": "Sygnały restartu i polityki nie są diagnozą przyczyny błędu."}
