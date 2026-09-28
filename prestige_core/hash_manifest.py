"""Manifesty Hash Checker dla folderów; SHA1/MD5 wyłącznie kompatybilność."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re

from .hashing import FileHashService


_LENGTHS = {"sha256": 64, "sha512": 128, "sha1": 40, "md5": 32}


def make_manifest(root, algorithm="sha256", *, max_files=10000, cancel_event=None):
    if algorithm not in _LENGTHS:
        raise ValueError("Nieobsługiwany algorytm.")
    root = Path(root)
    if root.is_symlink():
        raise ValueError("Katalog nie może być dowiązaniem.")
    root = root.resolve(strict=True)
    if not root.is_dir() or max_files < 1:
        raise ValueError("Wymagany katalog i dodatni limit plików.")
    files, errors, pending = {}, [], [root]
    while pending:
        if cancel_event is not None and cancel_event.is_set():
            errors.append({"path": ".", "error": "Przerwano skan."})
            break
        folder = pending.pop()
        try:
            with os.scandir(folder) as iterator:
                entries = sorted(iterator, key=lambda item: item.name)
        except OSError as error:
            errors.append({"path": str(folder.relative_to(root)), "error": type(error).__name__})
            continue
        for entry in entries:
            if cancel_event is not None and cancel_event.is_set():
                errors.append({"path": ".", "error": "Przerwano skan."})
                pending.clear()
                break
            relative = Path(entry.path).relative_to(root).as_posix()
            try:
                if entry.is_symlink():
                    errors.append({"path": relative, "error": "Pominięto dowiązanie."})
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    if len(files) >= max_files:
                        errors.append({"path": relative, "error": "Limit plików."})
                        pending.clear()
                        break
                    before = Path(entry.path).stat(follow_symlinks=False)
                    digest = FileHashService.hashes(entry.path, (algorithm,))[algorithm]
                    files[relative] = {"hash": digest, "size": before.st_size,
                                       "mtime_ns": before.st_mtime_ns}
            except (OSError, ValueError) as error:
                errors.append({"path": relative, "error": type(error).__name__})
    return {"schema_version": 1, "algorithm": algorithm, "root": str(root),
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "files": dict(sorted(files.items())), "errors": errors,
            "complete": not errors}


def validate_manifest(data):
    if (not isinstance(data, dict) or data.get("schema_version") != 1
            or data.get("algorithm") not in _LENGTHS or not isinstance(data.get("files"), dict)
            or type(data.get("complete")) is not bool):
        raise ValueError("Nieprawidłowy manifest.")
    for name, row in data["files"].items():
        if not isinstance(name, str):
            raise ValueError("Nieprawidłowa ścieżka w manifeście.")
        path = PurePosixPath(name)
        if (path.is_absolute() or not path.parts or ":" in path.parts[0]
                or any(part in {".", ".."} for part in path.parts) or "\\" in name
                or not isinstance(row, dict)
                or not isinstance(row.get("hash"), str)
                or not re.fullmatch(r"[0-9a-fA-F]{%d}" % _LENGTHS[data["algorithm"]], row["hash"])):
            raise ValueError("Nieprawidłowa ścieżka lub hash w manifeście.")
    return data


def compatible_manifest(data):
    """Czytaj manifest starego Hash Checker bez osłabiania walidacji nowych."""
    if (isinstance(data, dict) and data.get("schema_version") == 1
            and "complete" not in data and set(data) == {"schema_version", "algorithm", "files"}):
        data = {**data, "complete": True, "errors": [], "legacy_format": True}
    return validate_manifest(data)


def compare_manifests(before, after):
    before, after = validate_manifest(before), validate_manifest(after)
    if before["algorithm"] != after["algorithm"]:
        raise ValueError("Różne algorytmy manifestów.")
    if not before["complete"] or not after["complete"]:
        return {"status": "UNKNOWN", "reason": "Co najmniej jeden skan jest niepełny."}
    left, right = before["files"], after["files"]
    added = sorted(right.keys() - left.keys())
    removed = sorted(left.keys() - right.keys())
    changed = sorted(path for path in left.keys() & right.keys()
                     if left[path]["hash"].lower() != right[path]["hash"].lower())
    return {"status": "COMPLETE", "new": added, "missing": removed,
            "changed": changed, "unchanged": sorted(left.keys() & right.keys() - set(changed)),
            "ok": not (added or removed or changed)}


def save_manifest(data, destination):
    validate_manifest(data)
    if not data["complete"]:
        raise ValueError("Nie zapisuj niepełnego manifestu jako baseline.")
    if not isinstance(data.get("root"), str):
        raise ValueError("Manifest nie zawiera katalogu źródłowego.")
    root = Path(data["root"]).resolve(strict=True)
    path = Path(destination).resolve()
    if path.is_relative_to(root):
        raise ValueError("Manifest musi być poza badanym katalogiem.")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return path
