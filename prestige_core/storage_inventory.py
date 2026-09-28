"""Odczytowa inwentaryzacja dysków Windows bez otwierania PhysicalDrive."""

import json
import os
import subprocess


def read_disks(*, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Inwentaryzacja dysków wymaga Windows.")
    script = (
        "@(Get-Disk -ErrorAction Stop | ForEach-Object { "
        "$disk=$_; $parts=@(Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue | "
        "ForEach-Object { [pscustomobject]@{Number=$_.PartitionNumber; "
        "DriveLetter=$(if($_.DriveLetter){[string]$_.DriveLetter}else{$null}); "
        "IsBoot=$_.IsBoot; IsSystem=$_.IsSystem} }); "
        "[pscustomobject]@{Number=$disk.Number; FriendlyName=$disk.FriendlyName; "
        "UniqueId=$disk.UniqueId; Size=$disk.Size; BusType=$disk.BusType.ToString(); "
        "IsReadOnly=$disk.IsReadOnly; IsBoot=$disk.IsBoot; IsSystem=$disk.IsSystem; "
        "Partitions=$parts} }) | ConvertTo-Json -Compress -Depth 6"
    )
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
    try:
        proc = runner(command, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Odczyt dysków jest niedostępny: {error}") from error
    if proc.returncode:
        raise RuntimeError("Nie udało się odczytać listy dysków. Sprawdź usługę Storage i uprawnienia.")
    try:
        raw = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as error:
        raise RuntimeError("System zwrócił nieprawidłową listę dysków.") from error
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raise RuntimeError("Nieprawidłowy format listy dysków.")
    result = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            number = int(row["Number"])
            size = int(row["Size"])
        except (KeyError, TypeError, ValueError):
            continue
        partitions = row.get("Partitions") or []
        if isinstance(partitions, dict):
            partitions = [partitions]
        result.append({
            "number": number,
            "device": rf"\\.\PhysicalDrive{number}",
            "model": str(row.get("FriendlyName") or "Niedostępne"),
            "unique_id": str(row.get("UniqueId") or "Niedostępne"),
            "size_bytes": size,
            "bus": str(row.get("BusType") or "Niedostępne"),
            "read_only": row.get("IsReadOnly") if isinstance(row.get("IsReadOnly"), bool) else None,
            "system": bool(row.get("IsBoot") or row.get("IsSystem") or
                           any(part.get("IsBoot") or part.get("IsSystem") for part in partitions if isinstance(part, dict))),
            "volumes": sorted({str(part["DriveLetter"]).upper() + ":" for part in partitions
                               if isinstance(part, dict) and part.get("DriveLetter")}),
        })
    return sorted(result, key=lambda row: row["number"])
