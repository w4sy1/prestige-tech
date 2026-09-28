"""Ograniczone pomocnicze operacje plikowe dla PC Cleanup."""

import json
import os
from pathlib import Path
import uuid

from .hashing import FileHashService


def digest(path):
    return FileHashService.sha256(path)


def read_json(path, *, max_bytes=64 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise ValueError("Wymagany zwykły JSON do 64 MiB.")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inside(root, relative):
    root = Path(root).resolve(strict=True)
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts or ":" in str(rel):
        raise ValueError("Niebezpieczna ścieżka.")
    target = root / rel
    cursor = target
    while cursor != root:
        if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
            raise ValueError("Dowiązania nie są obsługiwane.")
        cursor = cursor.parent
    target.resolve().relative_to(root)
    return target


def files(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
        raise ValueError("Wymagany zwykły katalog.")
    result = []
    def fail(error):
        raise error
    for current, directories, names in os.walk(root, followlinks=False, onerror=fail):
        directories[:] = [name for name in directories if not (Path(current) / name).is_symlink()
                          and not (hasattr(Path(current) / name, "is_junction")
                                   and (Path(current) / name).is_junction())]
        for name in sorted(names):
            path = Path(current) / name
            if path.is_symlink():
                continue
            if path.is_file():
                result.append(path)
    return sorted(result)
