"""Kontrolowane zmiany istniejących DWORD HKCU Explorer z kopią i cofnięciem."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import uuid


SOURCE = "https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca"
ADVANCED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
DWM = r"Software\Microsoft\Windows\DWM"
PERSONALIZE_SOURCE = "https://learn.microsoft.com/en-us/windows/apps/develop/settings/settings-common"


@dataclass(frozen=True)
class ChangeOperation:
    id: str
    label: str
    key: str
    name: str
    target: int
    allowed: tuple[int, ...] = (0, 1)
    source: str = SOURCE


OPERATIONS = (
    ChangeOperation("REG-WRITE-002", "Pokaż pliki ukryte", ADVANCED, "Hidden", 1, (1, 2)),
    ChangeOperation("REG-WRITE-003", "Pokaż podgląd plików", ADVANCED, "ShowPreviewHandlers", 1),
    ChangeOperation("REG-WRITE-004", "Włącz pola wyboru plików", ADVANCED, "UseCheckBoxes", 1),
    ChangeOperation("REG-WRITE-005", "Włącz kreator udostępniania", ADVANCED, "SharingWizardOn", 1),
    ChangeOperation("REG-WRITE-006", "Pokaż miniatury zamiast samych ikon", ADVANCED, "IconsOnly", 0),
    ChangeOperation("REG-WRITE-007", "Pokaż dymki informacyjne", ADVANCED, "ShowInfoTip", 1),
    ChangeOperation("REG-WRITE-008", "Pokaż kolory plików NTFS", ADVANCED, "ShowCompColor", 1),
    ChangeOperation("REG-WRITE-009", "Otwieraj okna folderów w osobnym procesie", ADVANCED,
                    "SeparateProcess", 1),
    ChangeOperation("REG-WRITE-010", "Pokaż chronione pliki systemowe", ADVANCED,
                    "ShowSuperHidden", 1),
    ChangeOperation("REG-WRITE-011", "Pokaż ikonę typu na miniaturach", ADVANCED,
                    "ShowTypeOverlay", 1),
    ChangeOperation("REG-WRITE-016", "Pokaż pasek stanu Eksploratora", ADVANCED,
                    "ShowStatusBar", 1, (0, 1),
                    "https://learn.microsoft.com/en-us/windows/apps/develop/settings/settings-common"),
    ChangeOperation("REG-WRITE-017", "Włącz jasny motyw aplikacji", PERSONALIZE,
                    "AppsUseLightTheme", 1, (0, 1), PERSONALIZE_SOURCE),
    ChangeOperation("REG-WRITE-018", "Włącz jasny motyw interfejsu Windows", PERSONALIZE,
                    "SystemUsesLightTheme", 1, (0, 1), PERSONALIZE_SOURCE),
    ChangeOperation("REG-WRITE-019", "Wyłącz efekt przezroczystości", PERSONALIZE,
                    "EnableTransparency", 0, (0, 1), PERSONALIZE_SOURCE),
    ChangeOperation("REG-WRITE-020", "Pokaż kolor akcentu na paskach tytułu okien", DWM,
                    "ColorPrevalence", 1, (0, 1), PERSONALIZE_SOURCE),
)


def _reg(registry, platform):
    if (platform or os.name) != "nt":
        raise RuntimeError("Zmiana rejestru wymaga Windows.")
    if registry is None:
        import winreg as registry
    return registry


def _operation(operation_id):
    for item in OPERATIONS:
        if item.id == operation_id:
            return item
    raise ValueError("Operacja spoza zatwierdzonego katalogu.")


def _read(registry, operation):
    with registry.OpenKey(registry.HKEY_CURRENT_USER, operation.key, 0, registry.KEY_READ) as handle:
        value, kind = registry.QueryValueEx(handle, operation.name)
    if kind != registry.REG_DWORD or type(value) is not int or value not in operation.allowed:
        raise ValueError("Nieoczekiwany typ lub wartość DWORD; nie zmieniono rejestru.")
    return value


def _write(registry, operation, value):
    with registry.OpenKey(registry.HKEY_CURRENT_USER, operation.key, 0,
                          registry.KEY_SET_VALUE) as handle:
        registry.SetValueEx(handle, operation.name, 0, registry.REG_DWORD, value)


def _save_new(path, record):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _set_status(path, record, status):
    record = {**record, "status": status}
    temporary = Path(str(path) + "." + uuid.uuid4().hex + ".tmp")
    try:
        _save_new(temporary, record)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def plan_change(operation_id, *, registry=None, platform=None):
    operation = _operation(operation_id)
    registry = _reg(registry, platform)
    current = _read(registry, operation)
    return {"status": "PLAN", "operation": operation.id, "label": operation.label,
            "hive": "HKCU", "key": operation.key, "name": operation.name,
            "current": current, "target": operation.target,
            "change_needed": current != operation.target,
            "source": operation.source, "requires_backup": True}


def apply_change(operation_id, backup_path, *, accept_changes=False, registry=None,
                 platform=None):
    if not accept_changes:
        raise ValueError("Wymagana jawna zgoda na zmianę.")
    operation = _operation(operation_id)
    registry = _reg(registry, platform)
    previous = _read(registry, operation)
    if previous == operation.target:
        return {"status": "ALREADY_SET", "operation": operation.id, "backup": None}
    path = Path(backup_path)
    record = {"schema_version": 1, "operation": operation.id, "hive": "HKCU",
              "key": operation.key, "name": operation.name, "type": "REG_DWORD",
              "previous": previous, "applied": operation.target,
              "status": "PREPARED", "source": operation.source}
    _save_new(path, record)
    try:
        if _read(registry, operation) != previous:
            raise RuntimeError("Wartość zmieniła się przed zapisem; odmowa.")
        _write(registry, operation, operation.target)
        if _read(registry, operation) != operation.target:
            raise RuntimeError("Weryfikacja zapisu nie powiodła się.")
        _set_status(path, record, "APPLIED")
    except BaseException:
        try:
            current = _read(registry, operation)
            if current == operation.target:
                _write(registry, operation, previous)
            if _read(registry, operation) == previous:
                _set_status(path, record, "ROLLED_BACK")
            else:
                _set_status(path, record, "RECOVERY_NEEDED")
        except (OSError, ValueError, RuntimeError):
            _set_status(path, record, "RECOVERY_NEEDED")
        raise
    return {"status": "APPLIED", "operation": operation.id, "backup": str(path)}


def _rollback_record(backup_path):
    path = Path(backup_path)
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise ValueError("Nieprawidłowa kopia rejestru.")
    operation = _operation(record.get("operation"))
    if (record.get("hive") != "HKCU" or record.get("key") != operation.key
            or record.get("name") != operation.name or record.get("type") != "REG_DWORD"
            or record.get("applied") != operation.target
            or type(record.get("previous")) is not int
            or record["previous"] not in operation.allowed
            or record["previous"] == operation.target
            or record.get("status") not in ("APPLIED", "RECOVERY_NEEDED")):
        raise ValueError("Kopia nie odpowiada zatwierdzonej operacji.")
    return path, record, operation


def preview_rollback_change(backup_path, *, registry=None, platform=None):
    path, record, operation = _rollback_record(backup_path)
    registry = _reg(registry, platform)
    current = _read(registry, operation)
    return {"status": "PLAN" if current == operation.target else "REFUSED",
            "operation": operation.id, "hive": "HKCU", "key": operation.key,
            "name": operation.name, "current": current,
            "expected": operation.target, "restore": record["previous"],
            "backup": str(path), "change_needed": current == operation.target}


def export_change_diff(backup_path, destination, *, registry=None, platform=None):
    preview = preview_rollback_change(backup_path, registry=registry, platform=platform)
    report = {"schema_version": 1, "operation": preview["operation"],
              "hive": preview["hive"], "key": preview["key"], "name": preview["name"],
              "before": preview["restore"], "applied": preview["expected"],
              "current": preview["current"], "status": preview["status"],
              "note": "Bieżący odczyt jest chwilowy; eksport nie zmienia rejestru."}
    _save_new(destination, report)
    return report


def rollback_change(backup_path, *, accept_changes=False, registry=None, platform=None):
    if not accept_changes:
        raise ValueError("Wymagana jawna zgoda na cofnięcie.")
    path, record, operation = _rollback_record(backup_path)
    registry = _reg(registry, platform)
    if _read(registry, operation) != operation.target:
        raise ValueError("Wartość zmieniła się od wykonania operacji; odmowa nadpisania.")
    _write(registry, operation, record["previous"])
    if _read(registry, operation) != record["previous"]:
        raise RuntimeError("Weryfikacja cofnięcia nie powiodła się.")
    _set_status(path, record, "ROLLED_BACK")
    return {"status": "ROLLED_BACK", "operation": operation.id, "backup": str(path)}
