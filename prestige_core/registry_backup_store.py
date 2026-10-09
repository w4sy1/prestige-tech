"""Zarządzane lokalne kopie prostych zmian Registry Managera."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

from .registry_change import KEY as EXTENSIONS_KEY, OPERATION_ID as EXTENSIONS_ID, VALUE as EXTENSIONS_VALUE
from .registry_policy_changes import KEY as POLICY_KEY, OPERATIONS as POLICY_OPERATIONS
from .registry_transactions import OPERATIONS as CHANGE_OPERATIONS


def default_backup_dir():
    if os.name != "nt":
        return Path.home() / ".local" / "share" / "PrestigeTech" / "RegistryBackups"
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        local = str(Path.home() / "AppData" / "Local")
    return Path(local) / "PrestigeTech" / "RegistryBackups"


def new_backup_path(operation_id, *, folder=None):
    known = {EXTENSIONS_ID} | {item.id for item in CHANGE_OPERATIONS} | {
        item.id for item in POLICY_OPERATIONS}
    if operation_id not in known:
        raise ValueError("Operacja spoza katalogu kopii Registry.")
    directory = Path(folder) if folder is not None else default_backup_dir()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not directory.is_dir():
        raise OSError("Katalog kopii jest niedostępny.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return directory / f"registry-{stamp}-{operation_id.lower()}-{uuid.uuid4().hex}.json"


def _metadata(path):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(record, dict) or record.get("hive") != "HKCU" or record.get("type") != "REG_DWORD":
        return None
    operation_id = record.get("operation")
    if operation_id == EXTENSIONS_ID:
        if (record.get("schema_version") != 1 or record.get("key") != EXTENSIONS_KEY
                or record.get("name") != EXTENSIONS_VALUE
                or type(record.get("applied")) is not int or record["applied"] != 0
                or type(record.get("previous")) is not int or record["previous"] != 1):
            return None
        label = "Pokaż rozszerzenia plików"
        status = record.get("status", "APPLIED_OR_UNKNOWN")
        kind = "extensions"
    else:
        change = next((item for item in CHANGE_OPERATIONS if item.id == operation_id), None)
        policy = next((item for item in POLICY_OPERATIONS if item.id == operation_id), None)
        if change is not None:
            if (record.get("schema_version") != 1 or record.get("key") != change.key
                    or record.get("name") != change.name
                    or type(record.get("applied")) is not int or record["applied"] != change.target
                    or type(record.get("previous")) is not int
                    or record["previous"] not in change.allowed):
                return None
            label, status, kind = change.label, record.get("status"), "change"
        elif policy is not None:
            previous = record.get("previous")
            if (record.get("schema_version") != 2 or record.get("key") != POLICY_KEY
                    or record.get("name") != policy.name
                    or type(record.get("applied")) is not int or record["applied"] != 1
                    or type(record.get("key_existed")) is not bool
                    or (previous is not None and (type(previous) is not int or previous != 0))):
                return None
            label, status, kind = policy.label, record.get("status"), "policy"
        else:
            return None
    if status not in ("APPLIED", "APPLIED_OR_UNKNOWN", "RECOVERY_NEEDED",
                      "PREPARED", "ROLLED_BACK", "ABORTED_CONFLICT"):
        return None
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return None
    return {"operation": operation_id, "label": label, "status": status,
            "kind": kind, "path": str(path), "modified_utc": modified}


def list_backups(*, folder=None, limit=100):
    if not 1 <= limit <= 500:
        raise ValueError("Limit kopii musi mieścić się w zakresie 1–500.")
    directory = Path(folder) if folder is not None else default_backup_dir()
    if not directory.is_dir():
        return []
    rows = []
    for path in directory.glob("registry-*.json"):
        metadata = _metadata(path)
        if metadata is not None:
            rows.append(metadata)
    rows.sort(key=lambda item: item["modified_utc"], reverse=True)
    return rows[:limit]
