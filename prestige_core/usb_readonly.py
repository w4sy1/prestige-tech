"""Kontrolowane ustawienie programowego atrybutu read-only dysku USB Windows."""

import os
from pathlib import Path
import subprocess
import tempfile

from .storage_inventory import read_disks


def _selected_usb(number, expected_id, expected_size, disks_reader):
    if type(number) is not int or not 0 <= number <= 4096:
        raise ValueError("Nieprawidłowy numer dysku.")
    disks = [disk for disk in disks_reader() if disk["number"] == number]
    if len(disks) != 1:
        raise ValueError("Dysk nie jest jednoznacznie widoczny.")
    disk = disks[0]
    if (disk["bus"].upper() != "USB" or disk["system"]
            or disk["unique_id"] in ("", "Niedostępne")
            or disk["unique_id"] != expected_id
            or disk["size_bytes"] != expected_size):
        raise ValueError("Tożsamość USB, rozmiar lub status systemowy dysku się zmieniły.")
    return disk


def set_usb_readonly(number, expected_id, expected_size, *, disks_reader=read_disks,
                     runner=subprocess.run, admin_check=None, platform=None):
    """Ustaw atrybut DiskPart i potwierdź go ponownym odczytem Get-Disk."""
    if (platform or os.name) != "nt":
        raise RuntimeError("DiskPart wymaga Windows.")
    if admin_check is None:
        from .windows_repairs import _is_admin
        admin_check = _is_admin
    if not admin_check():
        raise PermissionError("Uruchom Storage & Recovery jako administrator.")
    disk = _selected_usb(number, expected_id, expected_size, disks_reader)
    if disk["read_only"] is True:
        return {"status": "ALREADY_READ_ONLY", "number": number,
                "unique_id": expected_id, "read_only": True}
    if disk["read_only"] is not False:
        raise ValueError("Stan zapisu USB jest nieznany; odśwież inwentaryzację.")
    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", suffix=".txt",
                                         prefix="prestige-diskpart-", delete=False) as stream:
            script_path = Path(stream.name)
            stream.write(f"select disk {number}\nattributes disk set readonly\n")
        # Numer i identyfikator sprawdzamy jeszcze raz bezpośrednio przed DiskPart.
        _selected_usb(number, expected_id, expected_size, disks_reader)
        result = runner(["diskpart.exe", "/s", str(script_path)], capture_output=True,
                        text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("DiskPart nie zakończył ustawiania tylko do odczytu.") from error
    finally:
        if script_path is not None:
            script_path.unlink(missing_ok=True)
    after = _selected_usb(number, expected_id, expected_size, disks_reader)
    if result.returncode != 0 or after["read_only"] is not True:
        raise RuntimeError("Atrybut tylko do odczytu nie został potwierdzony przez Get-Disk.")
    return {"status": "READ_ONLY_SET", "number": number,
            "unique_id": expected_id, "read_only": True}
