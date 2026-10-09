"""Wąska transakcja HKCU: pokaż rozszerzenia plików, z kopią i cofnięciem."""

import json
import os
from pathlib import Path

from .registry_transactions import _set_status


KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
VALUE = "HideFileExt"
OPERATION_ID = "REG-WRITE-001"
SOURCE = "https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/3c837e92-016e-4148-86e5-b4f0381a757f"


def _registry(registry, platform):
    if (platform or os.name) != "nt":
        raise RuntimeError("Zmiana rejestru wymaga Windows.")
    if registry is None:
        import winreg as registry
    return registry


def _current(registry, access):
    with registry.OpenKey(registry.HKEY_CURRENT_USER, KEY, 0, access) as handle:
        value, kind = registry.QueryValueEx(handle, VALUE)
    if kind != registry.REG_DWORD or type(value) is not int or value not in (0, 1):
        raise ValueError("Nieoczekiwany typ lub wartość HideFileExt; nic nie zmieniono.")
    return value


def _set(registry, value):
    with registry.OpenKey(registry.HKEY_CURRENT_USER, KEY, 0, registry.KEY_SET_VALUE) as handle:
        registry.SetValueEx(handle, VALUE, 0, registry.REG_DWORD, value)


def _backup(path, previous):
    record = {"schema_version": 1, "operation": OPERATION_ID, "hive": "HKCU",
              "key": KEY, "name": VALUE, "type": "REG_DWORD", "previous": previous,
              "applied": 0, "source": SOURCE, "status": "PREPARED"}
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return record


def show_file_extensions(backup_path, *, accept_changes=False, registry=None, platform=None):
    """Wykonaj tylko po jawnej zgodzie, zapisując nowy backup przed zmianą."""
    if not accept_changes:
        raise ValueError("Wymagana jawna zgoda na zmianę.")
    registry = _registry(registry, platform)
    previous = _current(registry, registry.KEY_READ)
    if previous == 0:
        return {"status": "ALREADY_SET", "backup": None}
    record = _backup(backup_path, previous)
    try:
        _set(registry, 0)
        if _current(registry, registry.KEY_READ) != 0:
            raise RuntimeError("Weryfikacja zmiany rejestru nie powiodła się.")
        _set_status(backup_path, record, "APPLIED")
    except BaseException:
        try:
            if _current(registry, registry.KEY_READ) == 0:
                _set(registry, previous)
            status = "ROLLED_BACK" if _current(registry, registry.KEY_READ) == previous else "RECOVERY_NEEDED"
            _set_status(backup_path, record, status)
        except (OSError, ValueError, RuntimeError):
            _set_status(backup_path, record, "RECOVERY_NEEDED")
        raise
    return {"status": "APPLIED", "backup": str(backup_path)}


def rollback_file_extensions(backup_path, *, accept_changes=False, registry=None, platform=None):
    """Cofnij tylko tę zmianę, jeśli aktualna wartość nadal równa się zapisanej."""
    if not accept_changes:
        raise ValueError("Wymagana jawna zgoda na cofnięcie.")
    registry = _registry(registry, platform)
    record = json.loads(Path(backup_path).read_text(encoding="utf-8"))
    if (not isinstance(record, dict) or record.get("schema_version") != 1
            or record.get("operation") != OPERATION_ID or record.get("hive") != "HKCU"
            or record.get("key") != KEY or record.get("name") != VALUE
            or record.get("type") != "REG_DWORD" or record.get("applied") != 0
            or record.get("previous") != 1
            or record.get("status", "APPLIED") not in ("APPLIED", "RECOVERY_NEEDED")):
        raise ValueError("Nieprawidłowa kopia dla tej operacji.")
    current = _current(registry, registry.KEY_READ)
    if current != record["applied"]:
        raise ValueError("Wartość zmieniła się od zapisu kopii; odmowa nadpisania.")
    _set(registry, record["previous"])
    if _current(registry, registry.KEY_READ) != record["previous"]:
        raise RuntimeError("Weryfikacja cofnięcia nie powiodła się.")
    _set_status(backup_path, record, "ROLLED_BACK")
    return {"status": "ROLLED_BACK", "backup": str(backup_path)}
