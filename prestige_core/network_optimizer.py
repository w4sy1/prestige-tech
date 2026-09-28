"""Odczyt ustawień interfejsu z Network Optimizer; bez zmian DNS/MTU."""

import base64
import json
import os
import subprocess


def inspect_adapter(index, *, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Odczyt optymalizacji wymaga Windows.")
    if type(index) is not int or not 1 <= index <= 65535:
        raise ValueError("Nieprawidłowy indeks interfejsu.")
    script = r'''
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$index=INDEX
$adapter=Get-NetAdapter -InterfaceIndex $index -ErrorAction Stop
$result=[ordered]@{index=$index;name=$adapter.Name;link_speed=$adapter.LinkSpeed;sections=[ordered]@{}}
try {
 $key='HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\'+$adapter.InterfaceGuid
 $setting=Get-ItemProperty -LiteralPath $key -ErrorAction Stop
 $result.sections.dns=[ordered]@{status='OK';servers=@((Get-DnsClientServerAddress -InterfaceIndex $index -AddressFamily IPv4 -ErrorAction Stop).ServerAddresses);automatic=[string]::IsNullOrWhiteSpace($setting.NameServer)}
} catch {$result.sections.dns=[ordered]@{status='UNKNOWN';error_type=$_.Exception.GetType().Name}}
try {$result.sections.mtu=[ordered]@{status='OK';data=@(Get-NetIPInterface -InterfaceIndex $index -AddressFamily IPv4 -ErrorAction Stop|Select-Object InterfaceIndex,NlMtu,ConnectionState,Dhcp,InterfaceMetric)}}
catch {$result.sections.mtu=[ordered]@{status='UNKNOWN';error_type=$_.Exception.GetType().Name}}
try {$result.sections.tcp=[ordered]@{status='OK';data=@(Get-NetTCPSetting -ErrorAction Stop|Select-Object SettingName,AutoTuningLevelLocal,CongestionProvider)}}
catch {$result.sections.tcp=[ordered]@{status='UNKNOWN';error_type=$_.Exception.GetType().Name}}
try {$result.sections.power=[ordered]@{status='OK';data=@(Get-NetAdapterPowerManagement -Name $adapter.Name -ErrorAction Stop|Select-Object Name,AllowComputerToTurnOffDevice,SelectiveSuspend,DeviceSleepOnDisconnect,WakeOnMagicPacket)}}
catch {$result.sections.power=[ordered]@{status='UNKNOWN';error_type=$_.Exception.GetType().Name}}
try {$result.sections.bindings=[ordered]@{status='OK';data=@(Get-NetAdapterBinding -Name $adapter.Name -ErrorAction Stop|Where-Object {$_.ComponentID -in @('ms_tcpip','ms_tcpip6')}|Select-Object ComponentID,Enabled)}}
catch {$result.sections.bindings=[ordered]@{status='UNKNOWN';error_type=$_.Exception.GetType().Name}}
try {$result.sections.dns_cache=[ordered]@{status='OK';count=@(Get-DnsClientCache -ErrorAction Stop).Count}}
catch {$result.sections.dns_cache=[ordered]@{status='UNKNOWN';error_type=$_.Exception.GetType().Name}}
$result|ConvertTo-Json -Depth 8 -Compress
'''.replace("INDEX", str(index))
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        result = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                        capture_output=True, text=True, encoding="utf-8", timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Nie odczytano ustawień interfejsu.") from error
    if result.returncode:
        raise RuntimeError("Nie odczytano ustawień interfejsu.")
    try:
        payload = json.loads((result.stdout or "").lstrip("\ufeff"))
    except json.JSONDecodeError as error:
        raise RuntimeError("Nieprawidłowy wynik ustawień interfejsu.") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("sections"), dict):
        raise RuntimeError("Nieprawidłowy format ustawień interfejsu.")
    return payload
