"""Odczytowy audyt konfiguracji Windows przeniesiony z Security Check."""
import base64
import json
import os
from pathlib import Path
import subprocess

from .security_rules import audit


def load_evidence(path, *, max_bytes=64 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Wymagany zwykły plik JSON.")
    if path.stat().st_size > max_bytes:
        raise ValueError("JSON przekracza limit rozmiaru.")
    return json.loads(path.read_text(encoding="utf-8-sig"))

CHECKS = {
 'defender': 'Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled',
 'firewall': 'Get-NetFirewallProfile | Select-Object Name,Enabled',
 'updates': "Get-Service wuauserv | Select-Object Status,StartType",
 'secure_boot': '[pscustomobject]@{Enabled=Confirm-SecureBootUEFI}',
 'tpm': 'Get-Tpm | Select-Object TpmPresent,TpmReady',
 'bitlocker': 'Get-BitLockerVolume | Select-Object MountPoint,ProtectionStatus',
 'uac': "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' | Select-Object EnableLUA",
 'smartscreen': "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer' | Select-Object SmartScreenEnabled",
 'rdp': "Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server' | Select-Object fDenyTSConnections",
 'smb': 'Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol,EnableSMB2Protocol,RequireSecuritySignature',
 'execution_policy': 'Get-ExecutionPolicy -List | ForEach-Object {[pscustomobject]@{Scope=[string]$_.Scope;ExecutionPolicy=[string]$_.ExecutionPolicy}}',
 'services': 'Get-CimInstance Win32_Service | ForEach-Object {[pscustomobject]@{Name=$_.Name;State=$_.State;StartMode=$_.StartMode;ExecutablePath=Get-SafeExecutable $_.PathName}}',
 'startup': 'Get-CimInstance Win32_StartupCommand | ForEach-Object {[pscustomobject]@{Name=$_.Name;Location=$_.Location;ExecutablePath=Get-SafeExecutable $_.Command}}',
 'tasks': 'Get-ScheduledTask | ForEach-Object {[pscustomobject]@{TaskName=$_.TaskName;TaskPath=$_.TaskPath;State=[string]$_.State;Executables=@($_.Actions|ForEach-Object {Get-SafeExecutable $_.Execute})}}',
 'proxy': "Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' | Select-Object ProxyEnable",
 'hosts': "Get-Content -LiteralPath (Join-Path $env:windir 'System32/drivers/etc/hosts') | Where-Object {$_ -match '^\\s*[^#\\s]'}",
 'dns': 'Get-DnsClientServerAddress | Select-Object InterfaceAlias,ServerAddresses',
 'ports': "Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess",
 'connections': 'Get-NetTCPConnection | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,State,OwningProcess',
 'detections': 'Get-MpThreatDetection | Select-Object -First 30 ThreatID,InitialDetectionTime,ActionSuccess',
 'processes': "Get-Process | ForEach-Object {$s='Unknown';if($_.Path){try{$s=[string](Get-AuthenticodeSignature -LiteralPath $_.Path).Status}catch{}};[pscustomobject]@{PID=$_.Id;Name=$_.ProcessName;Path=$_.Path;Signature=$s}}",
}

def _powershell(script, timeout=180, *, runner=subprocess.run):
    encoded = base64.b64encode(("[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
                                "$ErrorActionPreference='Stop';" + script).encode("utf-16le")).decode("ascii")
    try:
        result = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                        capture_output=True, text=True, encoding="utf-8", timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Nie ukończono odczytu Security Check.") from error
    if result.returncode:
        raise RuntimeError("PowerShell nie ukończył odczytu Security Check.")
    try:
        return json.loads(result.stdout.lstrip("\ufeff"))
    except json.JSONDecodeError as error:
        raise RuntimeError("Security Check zwrócił nieprawidłowy JSON.") from error


def collect(*, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Odczyt Security Check wymaga Windows.")
    pieces=[]
    for name, script in CHECKS.items():
        pieces.append(f"try {{$r['{name}']=@{{status='OK';data=@({script})}}}} catch {{$r['{name}']=@{{status='UNKNOWN';error=$_.Exception.GetType().Name;data=@()}}}}")
    helpers=r'''function Get-SafeExecutable($value){
      if($value -match '^"([^"]+)"'){return $Matches[1]}
      if($value -match '^(.+?\.(?:exe|com|cmd|bat|ps1|vbs|js))(?=\s|$)'){return $Matches[1]}
      return '[nierozpoznana ścieżka]'
    };'''
    return _powershell(helpers+'$r=[ordered]@{};'+';'.join(pieces)+';$r | ConvertTo-Json -Depth 8',
                       runner=runner)

def audit_windows(*, runner=subprocess.run, platform=None):
    return audit(collect(runner=runner, platform=platform))
