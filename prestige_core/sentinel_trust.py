"""Kontrolowana zmiana listy zaufanych urządzeń Sentinel z kopią i cofnięciem."""

import base64
import hashlib
import json
import os
from pathlib import Path
import uuid

def _raw(path):
    source = Path(path)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 1024 * 1024:
        raise ValueError("Wymagany zwykły plik listy Sentinel do 1 MiB.")
    data = source.read_bytes()
    rows = json.loads(data.decode("utf-8-sig"))
    if (not isinstance(rows, list) or
            any(not isinstance(row, dict) or not isinstance(row.get("Key"), str)
                or not row["Key"].strip() for row in rows)):
        raise ValueError("Niepełna lista Sentinel; odmowa zmiany.")
    keys = [row["Key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Powtórzone klucze Sentinel; odmowa zmiany.")
    return data, rows


def _replace(path, payload):
    path = Path(path)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def change_trust(known_path, trusted_path, key, enable):
    if not isinstance(key, str) or not key or type(enable) is not bool:
        raise ValueError("Wybierz urządzenie i operację zaufania.")
    known_file, trusted_file = Path(known_path), Path(trusted_path)
    if known_file.parent.resolve() != trusted_file.parent.resolve():
        raise ValueError("Listy Sentinel muszą pochodzić z jednego katalogu.")
    known_bytes, known = _raw(known_file)
    original, trusted = _raw(trusted_file)
    known_row = next((row for row in known if row["Key"] == key), None)
    if known_row is None:
        raise ValueError("Urządzenia nie ma na liście znanych.")
    present = any(row["Key"] == key for row in trusted)
    if present == enable:
        return {"status": "UNCHANGED"}
    changed = trusted + [{name: known_row.get(name, "") for name in
                          ("Key", "IP", "MAC", "Name", "Added")}] if enable else [
                              row for row in trusted if row["Key"] != key]
    payload = (json.dumps(changed, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    backup = trusted_file.with_name(trusted_file.name + "." + uuid.uuid4().hex + ".trust-backup.json")
    record = {"schema_version": 1, "operation": "sentinel-trust", "target": str(trusted_file.resolve()),
              "known_sha256": hashlib.sha256(known_bytes).hexdigest(),
              "before_sha256": hashlib.sha256(original).hexdigest(),
              "after_sha256": hashlib.sha256(payload).hexdigest(),
              "original_base64": base64.b64encode(original).decode("ascii"),
              "key": key, "trusted": enable}
    with backup.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    if (hashlib.sha256(_raw(trusted_file)[0]).hexdigest() != record["before_sha256"]
            or hashlib.sha256(_raw(known_file)[0]).hexdigest() != record["known_sha256"]):
        raise RuntimeError("Lista Sentinel zmieniła się przed zapisem; kopia zachowana.")
    _replace(trusted_file, payload)
    if hashlib.sha256(_raw(trusted_file)[0]).hexdigest() != record["after_sha256"]:
        raise RuntimeError("Nie potwierdzono zmiany listy; użyj kopii do cofnięcia.")
    return {"status": "APPLIED", "backup": str(backup), "key": key, "trusted": enable}


def rollback_trust(trusted_path, backup_path):
    target = Path(trusted_path)
    record = json.loads(Path(backup_path).read_text(encoding="utf-8-sig"))
    if (not isinstance(record, dict) or record.get("schema_version") != 1
            or record.get("operation") != "sentinel-trust"
            or record.get("target") != str(target.resolve())):
        raise ValueError("Kopia nie dotyczy wybranej listy Sentinel.")
    original = base64.b64decode(record["original_base64"], validate=True)
    if hashlib.sha256(original).hexdigest() != record.get("before_sha256"):
        raise ValueError("Kopia listy Sentinel jest uszkodzona.")
    current, _ = _raw(target)
    if hashlib.sha256(current).hexdigest() != record.get("after_sha256"):
        raise RuntimeError("Lista zaufanych zmieniła się później; odmowa nadpisania.")
    _replace(target, original)
    return {"status": "ROLLED_BACK", "target": str(target)}
