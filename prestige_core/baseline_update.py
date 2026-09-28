"""Kontrolowana aktualizacja baseline integralności z kopią poprzedniej wersji."""

import json
import os
from pathlib import Path
import shutil
import uuid

from .file_snapshot import compare_files


def update_baseline(path, current, *, accept_changes=False):
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError("Baseline musi być istniejącym zwykłym plikiem, bez symlinku.")
    if not current.get("complete"):
        raise ValueError("Nie wolno aktualizować baseline z niepełnego skanu.")
    root = Path(current["root"]).resolve(strict=True)
    if target.resolve().is_relative_to(root):
        raise ValueError("Baseline musi znajdować się poza katalogiem źródłowym.")
    previous = json.loads(target.read_text(encoding="utf-8"))
    comparison = compare_files(previous, current)
    if comparison["status"] != "COMPLETE":
        raise ValueError("Poprzedni lub bieżący baseline jest niepełny.")
    if not accept_changes:
        return {"updated": False, "comparison": comparison}
    backup = target.with_name(target.name + "." + uuid.uuid4().hex + ".bak")
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    with target.open("rb") as source, backup.open("xb") as destination:
        shutil.copyfileobj(source, destination)
        destination.flush()
        os.fsync(destination.fileno())
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(current, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return {"updated": True, "backup": str(backup), "comparison": comparison}
