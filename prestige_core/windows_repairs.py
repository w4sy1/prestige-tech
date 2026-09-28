"""Plany i kontrolowane wykonanie sześciu napraw Windows Toolkit."""

import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import uuid


OPERATIONS = {
    "sfc": (["sfc.exe", "/scannow"], 7200, "Kontrola i naprawa plików systemowych"),
    "dism-scan": (["dism.exe", "/Online", "/Cleanup-Image", "/ScanHealth"], 7200,
                  "Skan stanu obrazu Windows"),
    "dism-restore": (["dism.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"], 14400,
                     "Naprawa obrazu Windows; możliwy pobór danych"),
    "flush-dns": (["ipconfig.exe", "/flushdns"], 60, "Czyszczenie cache DNS"),
    "winsock-reset": (["netsh.exe", "winsock", "reset"], 120,
                      "Reset Winsock; zwykle wymagany restart"),
    "dhcp-renew": (["ipconfig.exe", "/renew"], 180,
                   "Odnowienie DHCP; może przerwać połączenie"),
}


def plan_repair(operation):
    if operation not in OPERATIONS:
        raise ValueError("Nieznana operacja naprawcza.")
    command, timeout, description = OPERATIONS[operation]
    return {"status": "PLAN", "operation": operation, "command": command.copy(),
            "timeout_seconds": timeout, "description": description,
            "requires_admin": True, "rollback_available": False,
            "note": "Brak gwarantowanego cofnięcia. Wymaga kopii diagnostycznej i świadomej zgody."}


def _is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def run_repair(operation, journal_directory, *, accept_no_rollback=False,
               runner=subprocess.run, admin_check=_is_admin, snapshot=None, platform=None):
    plan = plan_repair(operation)
    if (platform or os.name) != "nt":
        raise RuntimeError("Naprawy wymagają Windows.")
    if not accept_no_rollback:
        raise ValueError("Potwierdź brak gwarantowanego cofnięcia.")
    if not admin_check():
        raise PermissionError("Uruchom System Center jako administrator.")
    if snapshot is None:
        from prestige_core.windows_toolkit import collect
        snapshot = collect()
    directory = Path(journal_directory).resolve()
    if not directory.is_dir():
        raise ValueError("Wybierz istniejący katalog dziennika poza katalogami systemowymi.")
    journal = directory / ("prestige-repair-" + uuid.uuid4().hex + ".json")
    record = {"schema_version": 1, "operation": operation, "command": plan["command"],
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "status": "STARTED", "rollback_available": False, "snapshot": snapshot}
    with journal.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        completed = runner(plan["command"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", check=False,
                           timeout=plan["timeout_seconds"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        record["exit_code"] = completed.returncode
        record["status"] = "COMPLETE" if completed.returncode in (0, 3010) else "FAILED"
        record["output_tail"] = (completed.stdout or "")[-4000:]
        record["error_tail"] = (completed.stderr or "")[-2000:]
    except (OSError, subprocess.TimeoutExpired) as error:
        record["status"] = "UNKNOWN"
        record["error_type"] = type(error).__name__
    with journal.open("w", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    return {"status": record["status"], "operation": operation,
            "exit_code": record.get("exit_code"), "restart_required": record.get("exit_code") == 3010,
            "journal": str(journal), "rollback_available": False}
