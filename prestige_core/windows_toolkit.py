"""Odczytowa diagnostyka Windows Toolkit dla System Center."""

from datetime import datetime, timezone
import os

from .security_check import _powershell


QUERIES = {
    "available_updates": """$job=Start-Job -ScriptBlock {
        $ErrorActionPreference='Stop';$s=New-Object -ComObject Microsoft.Update.Session;
        $u=$s.CreateUpdateSearcher().Search("IsInstalled=0 and IsHidden=0 and Type='Software'");
        [pscustomobject]@{ResultCode=[int]$u.ResultCode;Updates=@(foreach($item in $u.Updates){
            [pscustomobject]@{Title=$item.Title;KB=@($item.KBArticleIDs);
                Downloaded=$item.IsDownloaded;RebootRequired=$item.RebootRequired;Mandatory=$item.IsMandatory}})}
        };try{if(-not (Wait-Job $job -Timeout 45)){throw [TimeoutException]::new()};
            Receive-Job $job -ErrorAction Stop}finally{
            Stop-Job $job -ErrorAction SilentlyContinue;
            Remove-Job $job -Force -ErrorAction SilentlyContinue}""",
    "physical_disks": "Get-PhysicalDisk -ErrorAction Stop | Select-Object FriendlyName,MediaType,HealthStatus,OperationalStatus,Size",
    "smart": "Get-PhysicalDisk -ErrorAction Stop | Get-StorageReliabilityCounter -ErrorAction Stop | Select-Object DeviceId,Temperature,Wear,PowerOnHours,ReadErrorsTotal,WriteErrorsTotal",
    "partitions": "Get-Partition -ErrorAction Stop | Select-Object DiskNumber,PartitionNumber,DriveLetter,Size,Type",
    "firmware": "Get-ComputerInfo -Property BiosFirmwareType -ErrorAction Stop | Select-Object BiosFirmwareType",
    "serial": "Get-CimInstance Win32_BIOS -ErrorAction Stop | Select-Object SerialNumber",
    "uptime": "Get-CimInstance Win32_OperatingSystem -ErrorAction Stop | Select-Object @{n='Seconds';e={[math]::Round(((Get-Date)-$_.LastBootUpTime).TotalSeconds)}}",
    "activation": "Get-CimInstance SoftwareLicensingProduct -Filter \"ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f'\" -ErrorAction Stop | Where-Object PartialProductKey | Select-Object Name,LicenseStatus",
    "run_registry": """foreach($hive in @('HKCU:','HKLM:')){foreach($key in @('Run','RunOnce')){
        $path="$hive\\Software\\Microsoft\\Windows\\CurrentVersion\\$key";
        if(Test-Path -LiteralPath $path){$item=Get-Item -LiteralPath $path -ErrorAction Stop;
            foreach($name in $item.GetValueNames()){
                [pscustomobject]@{Key=$path;Name=$name;
                    ValuePresent=([string]$item.GetValue($name)).Length -gt 0}}}}}""",
    "events": """foreach($log in @('System','Application')){
        try{Get-WinEvent -FilterHashtable @{LogName=$log;Level=1,2,3;
            StartTime=(Get-Date).AddDays(-7)} -MaxEvents 30 -ErrorAction Stop |
            Select-Object TimeCreated,Id,LevelDisplayName,ProviderName,LogName}
        catch{if($_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*'){throw}}}""",
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
    result = _powershell(script, 180, **options)
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
