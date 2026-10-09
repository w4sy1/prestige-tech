"""Manifest sum kontrolnych plików dołączonych jako odniesienia do raportu."""

import hashlib
import json
from pathlib import Path


def attachment_manifest(paths, destination):
    if len(paths) > 20:
        raise ValueError("Raport obsługuje maksymalnie 20 odniesień do plików.")
    rows = []
    for raw in paths:
        path = Path(raw)
        if not path.is_file() or path.stat().st_size > 2 * 1024 ** 3:
            raise ValueError("Załącznik nie istnieje lub przekracza 2 GiB.")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        rows.append({"name": path.name, "size": path.stat().st_size, "sha256": digest.hexdigest()})
    target = Path(destination)
    with target.open("x", encoding="utf-8") as stream:
        json.dump({"schema_version": 1, "attachments": rows,
                   "note": "Pliki nie są kopiowane; manifest zapisuje nazwy, rozmiary i SHA-256."},
                  stream, ensure_ascii=False, indent=2)
    return str(target)
