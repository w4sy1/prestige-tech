"""Udokumentowane polityki HKCU z kopią także nieistniejącej wartości."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import uuid


KEY = r"Software\Policies\Microsoft\Windows\Explorer"


@dataclass(frozen=True)
class PolicyChange:
    id: str
    label: str
    name: str
    source: str


OPERATIONS = (
    PolicyChange(
        "REG-WRITE-012", "Nie zapisuj historii wyszukiwania Eksploratora",
        "DisableSearchBoxSuggestions",
        "https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-windowsexplorer#disablesearchboxsuggestions"),
    PolicyChange(
        "REG-WRITE-013", "Ukryj Centrum powiadomień na pasku zadań",
        "DisableNotificationCenter",
        "https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-taskbar#disablenotificationcenter"),
    PolicyChange(
        "REG-WRITE-014", "Ukryj fragmenty treści w widoku zawartości Eksploratora",
        "HideContentViewModeSnippets",
        "https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-windowsexplorer#hidecontentviewmodesnippets"),
    PolicyChange(
        "REG-WRITE-015", "Nie zapisuj miniatur w plikach thumbs.db na dyskach sieciowych",
        "DisableThumbsDBOnNetworkFolders",
        "https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-admx-thumbnails#disablethumbsdbonnetworkfolders"),
)


def _operation(operation_id):
    for operation in OPERATIONS:
        if operation.id == operation_id:
            return operation
    raise ValueError("Operacja spoza katalogu polityk.")


def _registry(registry, platform):
    if (platform or os.name) != "nt":
        raise RuntimeError("Zmiana rejestru wymaga Windows.")
    if registry is None:
        import winreg as registry
    return registry


def _check_host_support(registry, platform, allow_unsupported=False):
    """Odmów na niewspieranej edycji; fixtury wstrzykują własny rejestr."""
    if registry is not None:
        return True
    if (platform or os.name) != "nt":
        return True
    build = sys.getwindowsversion().build
    if build < 19041:
        raise RuntimeError("Ta polityka wymaga Windows 10 2004+ lub Windows 11.")
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as handle:
        edition, kind = winreg.QueryValueEx(handle, "EditionID")
    if kind != winreg.REG_SZ or not isinstance(edition, str):
        raise RuntimeError("Nie udało się ustalić edycji Windows.")
    if not any(token in edition.casefold() for token in
               ("professional", "enterprise", "education", "iotenterprise")):
        if not allow_unsupported:
            raise RuntimeError("Ta polityka jest wspierana w Windows Pro/Enterprise/Education. "
                               "Włącz tryb eksperymentalny, jeśli świadomie chcesz spróbować na tej edycji.")
        return False
    return True


def _read(registry, operation):
    try:
        with registry.OpenKey(registry.HKEY_CURRENT_USER, KEY, 0,
                              registry.KEY_READ) as handle:
            try:
                value, kind = registry.QueryValueEx(handle, operation.name)
            except FileNotFoundError:
                return True, None
    except FileNotFoundError:
        return False, None
    if kind != registry.REG_DWORD or type(value) is not int or value not in (0, 1):
        raise ValueError("Istniejąca polityka ma nieoczekiwany typ lub wartość; odmowa.")
    return True, value


def _set(registry, operation, value):
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, KEY, 0,
                              registry.KEY_SET_VALUE) as handle:
        registry.SetValueEx(handle, operation.name, 0, registry.REG_DWORD, value)


def _restore(registry, operation, key_existed, previous):
    if previous is not None:
        _set(registry, operation, previous)
        return
    with registry.OpenKey(registry.HKEY_CURRENT_USER, KEY, 0,
                          registry.KEY_SET_VALUE) as handle:
        registry.DeleteValue(handle, operation.name)
    # Usuwamy klucz tylko wtedy, gdy utworzyła go ta transakcja i jest pusty.
    if not key_existed:
        try:
            registry.DeleteKey(registry.HKEY_CURRENT_USER, KEY)
        except OSError:
            pass


def _save_new(path, record):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _status(path, record, status):
    temporary = Path(str(path) + "." + uuid.uuid4().hex + ".tmp")
    try:
        _save_new(temporary, {**record, "status": status})
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def plan_policy_change(operation_id, *, registry=None, platform=None,
                       allow_unsupported=False):
    operation = _operation(operation_id)
    supported = _check_host_support(registry, platform, allow_unsupported)
    registry = _registry(registry, platform)
    key_existed, current = _read(registry, operation)
    return {"status": "PLAN", "operation": operation.id, "label": operation.label,
            "hive": "HKCU", "key": KEY, "name": operation.name,
            "key_existed": key_existed, "current": current, "target": 1,
            "change_needed": current != 1, "source": operation.source,
            "supported_edition": supported}


def apply_policy_change(operation_id, backup_path, *, accept_changes=False,
                        registry=None, platform=None, allow_unsupported=False):
    if not accept_changes:
        raise ValueError("Wymagana jawna zgoda na zmianę.")
    operation = _operation(operation_id)
    supported = _check_host_support(registry, platform, allow_unsupported)
    registry = _registry(registry, platform)
    key_existed, previous = _read(registry, operation)
    if previous == 1:
        return {"status": "ALREADY_SET", "operation": operation.id, "backup": None}
    path = Path(backup_path)
    record = {"schema_version": 2, "operation": operation.id, "hive": "HKCU",
              "key": KEY, "name": operation.name, "type": "REG_DWORD",
              "key_existed": key_existed, "previous": previous, "applied": 1,
              "source": operation.source, "supported_edition": supported,
              "status": "PREPARED"}
    _save_new(path, record)
    write_attempted = False
    try:
        if _read(registry, operation) != (key_existed, previous):
            raise RuntimeError("Polityka zmieniła się przed zapisem; odmowa.")
        write_attempted = True
        _set(registry, operation, 1)
        if _read(registry, operation)[1] != 1:
            raise RuntimeError("Weryfikacja zapisu nie powiodła się.")
        _status(path, record, "APPLIED")
    except BaseException:
        if not write_attempted:
            _status(path, record, "ABORTED_CONFLICT")
            raise
        try:
            current = _read(registry, operation)
            if current[1] == 1:
                _restore(registry, operation, key_existed, previous)
            elif previous is None and not key_existed and current == (True, None):
                try:
                    registry.DeleteKey(registry.HKEY_CURRENT_USER, KEY)
                except OSError:
                    pass
            if _read(registry, operation) == (key_existed, previous):
                _status(path, record, "ROLLED_BACK")
            else:
                _status(path, record, "RECOVERY_NEEDED")
        except (OSError, ValueError, RuntimeError):
            _status(path, record, "RECOVERY_NEEDED")
        raise
    return {"status": "APPLIED", "operation": operation.id, "backup": str(path)}


def _record(backup_path):
    path = Path(backup_path)
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowa kopia polityki.")
    operation = _operation(record.get("operation"))
    if (record.get("schema_version") != 2 or record.get("hive") != "HKCU"
            or record.get("key") != KEY or record.get("name") != operation.name
            or record.get("type") != "REG_DWORD" or record.get("applied") != 1
            or type(record.get("key_existed")) is not bool
            or (record.get("previous") is not None
                and (type(record["previous"]) is not int or record["previous"] != 0))
            or (record["previous"] is not None and not record["key_existed"])
            or record.get("status") not in ("APPLIED", "RECOVERY_NEEDED")):
        raise ValueError("Kopia nie odpowiada zatwierdzonej polityce.")
    return path, record, operation


def preview_policy_rollback(backup_path, *, registry=None, platform=None):
    path, record, operation = _record(backup_path)
    registry = _registry(registry, platform)
    current = _read(registry, operation)[1]
    return {"status": "PLAN" if current == 1 else "REFUSED",
            "operation": operation.id, "name": operation.name, "current": current,
            "restore": record["previous"], "backup": str(path)}


def rollback_policy_change(backup_path, *, accept_changes=False,
                           registry=None, platform=None):
    if not accept_changes:
        raise ValueError("Wymagana jawna zgoda na cofnięcie.")
    path, record, operation = _record(backup_path)
    registry = _registry(registry, platform)
    if _read(registry, operation)[1] != 1:
        raise ValueError("Polityka zmieniła się od wykonania operacji; odmowa.")
    try:
        _restore(registry, operation, record["key_existed"], record["previous"])
        if _read(registry, operation) != (record["key_existed"], record["previous"]):
            raise RuntimeError("Weryfikacja cofnięcia nie powiodła się.")
    except (OSError, ValueError, RuntimeError):
        _status(path, record, "RECOVERY_NEEDED")
        raise
    _status(path, record, "ROLLED_BACK")
    return {"status": "ROLLED_BACK", "operation": operation.id, "backup": str(path)}
