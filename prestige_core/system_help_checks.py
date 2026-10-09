"""Odczyt stanu drukowania i urządzeń dźwięku bez zmiany Windows."""

import os

from .security_check import _powershell


PRINTER_SCRIPT = r'''
$r=[ordered]@{status='UNKNOWN';service='UNKNOWN';printers=@();error_type=$null}
try {
  $r.service=[string](Get-Service -Name Spooler -ErrorAction Stop).Status
  $r.printers=@(Get-Printer -ErrorAction Stop | ForEach-Object {
    [ordered]@{name=[string]$_.Name;printer_status=[string]$_.PrinterStatus;
      job_count=[int](Get-PrintJob -PrinterName $_.Name -ErrorAction SilentlyContinue | Measure-Object).Count}
  })
  $r.status='COMPLETE'
} catch { $r.error_type=$_.Exception.GetType().Name }
ConvertTo-Json -InputObject $r -Depth 5 -Compress
'''

AUDIO_SCRIPT = r'''
$r=[ordered]@{status='UNKNOWN';devices=@();error_type=$null}
try {
  $r.devices=@(Get-CimInstance Win32_SoundDevice -ErrorAction Stop | ForEach-Object {
    [ordered]@{name=[string]$_.Name;status=[string]$_.Status;
      error_code=[int]$_.ConfigManagerErrorCode}
  })
  $r.status='COMPLETE'
} catch { $r.error_type=$_.Exception.GetType().Name }
ConvertTo-Json -InputObject $r -Depth 5 -Compress
'''


def read_printer_state(*, platform=None, powershell=_powershell):
    if (platform or os.name) != "nt":
        raise RuntimeError("Odczyt drukarki wymaga Windows.")
    result = powershell(PRINTER_SCRIPT, timeout=30)
    if not isinstance(result, dict) or result.get("status") not in ("COMPLETE", "UNKNOWN"):
        raise ValueError("Nieprawidłowy wynik odczytu drukarki.")
    return {"status": result["status"], "service": result.get("service", "UNKNOWN"),
            "printers": result.get("printers", []), "error_type": result.get("error_type"),
            "system_changed": False, "note": "Odczyt nie resetuje kolejki ani usługi drukowania."}


def read_audio_devices(*, platform=None, powershell=_powershell):
    if (platform or os.name) != "nt":
        raise RuntimeError("Odczyt dźwięku wymaga Windows.")
    result = powershell(AUDIO_SCRIPT, timeout=30)
    if not isinstance(result, dict) or result.get("status") not in ("COMPLETE", "UNKNOWN"):
        raise ValueError("Nieprawidłowy wynik odczytu dźwięku.")
    return {"status": result["status"], "devices": result.get("devices", []),
            "error_type": result.get("error_type"), "default_output": "UNKNOWN",
            "mute": "UNKNOWN", "system_changed": False,
            "note": "Odczyt urządzeń nie ustala domyślnego wyjścia ani wyciszenia."}
