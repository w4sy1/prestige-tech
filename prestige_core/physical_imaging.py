"""Konserwatywna akwizycja RAW dysku read-only; bez twierdzenia o sprzętowym blockerze."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from .storage_inventory import read_disks


def destination_disk_number(destination, *, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Identyfikacja dysku celu wymaga Windows.")
    parent = Path(destination).parent.resolve(strict=True)
    drive = parent.drive
    if not re.fullmatch(r"[A-Za-z]:", drive):
        raise ValueError("Cel musi znajdować się na lokalnym woluminie z literą dysku.")
    script = (f"$p=Get-Partition -DriveLetter '{drive[0]}' -ErrorAction Stop; "
              "if(@($p).Count -ne 1){throw 'Ambiguous partition'}; "
              "[int]$p.DiskNumber")
    try:
        result = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                        capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Nie ustalono dysku docelowego.") from error
    if result.returncode:
        raise RuntimeError("Nie ustalono dysku docelowego.")
    try:
        number = int(result.stdout.strip())
    except ValueError as error:
        raise RuntimeError("Nieprawidłowy numer dysku docelowego.") from error
    if number < 0:
        raise RuntimeError("Nieprawidłowy numer dysku docelowego.")
    return number


def image_readonly_disk(number, destination, *, cancel_event=None, disks_reader=read_disks,
                        target_resolver=destination_disk_number, source_opener=open,
                        chunk_size=1024 * 1024, platform=None):
    """Czytaj dokładnie rozmiar z Get-Disk; pozostaw INCOMPLETE po błędzie/przerwaniu."""
    if (platform or os.name) != "nt":
        raise RuntimeError("Obraz fizycznego dysku wymaga Windows.")
    if type(number) is not int or not 0 <= number <= 4096:
        raise ValueError("Nieprawidłowy numer PhysicalDrive.")
    if not 4096 <= chunk_size <= 16 * 1024 * 1024:
        raise ValueError("Niedozwolony rozmiar bufora.")
    destination = Path(destination)
    metadata_path = Path(str(destination) + ".json")
    if destination.suffix.lower() != ".img":
        raise ValueError("Obraz musi mieć rozszerzenie .img.")
    if destination.exists() or metadata_path.exists():
        raise FileExistsError("Obraz lub jego metadane już istnieją.")
    parent = destination.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("Katalog docelowy nie istnieje.")
    disks = [disk for disk in disks_reader() if disk["number"] == number]
    if len(disks) != 1:
        raise ValueError("Nie znaleziono jednoznacznego dysku źródłowego.")
    disk = disks[0]
    if disk["system"]:
        raise ValueError("Ten tryb odmawia obrazowania dysku systemowego.")
    if disk["read_only"] is not True:
        raise ValueError("Źródło nie ma potwierdzonego atrybutu tylko do odczytu.")
    size = disk["size_bytes"]
    if type(size) is not int or size <= 0:
        raise ValueError("Nieprawidłowy rozmiar dysku źródłowego.")
    if target_resolver(destination) == number:
        raise ValueError("Dysk docelowy jest tym samym dyskiem co źródło.")
    if shutil.disk_usage(parent).free < size + 1024 * 1024:
        raise ValueError("Za mało miejsca na obraz i metadane.")
    metadata = {"schema_version": 1, "mode": "physical_readonly", "source_number": number,
                "source_unique_id": disk["unique_id"], "expected_bytes": size,
                "read_bytes": 0, "sha256_image": None, "verified_image": False,
                "status": "INCOMPLETE", "error": None,
                "write_protection": "Windows IsReadOnly; brak gwarancji sprzętowej blokady",
                "started_at_utc": datetime.now(timezone.utc).isoformat()}
    digest = hashlib.sha256()
    error = None
    try:
        with source_opener(disk["device"], "rb", buffering=0) as source:
            with destination.open("xb") as output:
                while metadata["read_bytes"] < size:
                    if cancel_event is not None and cancel_event.is_set():
                        error = "Przerwano na żądanie użytkownika."
                        break
                    block = source.read(min(chunk_size, size - metadata["read_bytes"]))
                    if not block:
                        error = "Odczyt źródła zakończył się przed oczekiwanym rozmiarem."
                        break
                    output.write(block)
                    digest.update(block)
                    metadata["read_bytes"] += len(block)
                output.flush()
                os.fsync(output.fileno())
        metadata["sha256_image"] = digest.hexdigest()
        if error is None and metadata["read_bytes"] == size:
            verification = hashlib.sha256()
            with destination.open("rb") as output:
                for block in iter(lambda: output.read(chunk_size), b""):
                    verification.update(block)
            metadata["verified_image"] = verification.digest() == digest.digest()
            if not metadata["verified_image"]:
                error = "Ponowny odczyt obrazu wykazał niezgodność SHA-256."
    except FileExistsError:
        raise
    except OSError as caught:
        error = f"Błąd I/O: {type(caught).__name__}"
    metadata["status"] = "INCOMPLETE" if error else "COMPLETE"
    metadata["error"] = error
    metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return metadata
