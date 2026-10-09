"""Odczytowa migawka plików dla przyszłego Monitora."""

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess

from .hashing import FileHashService
from .file_extended import collect_extended, metadata_complete


def scan_files(root, *, max_files=10000, cancel_event=None, previous=None,
               force_rehash=False, extended=False, exclude_paths=()):
    """Hashuj zwykłe pliki, pomijaj symlinki, zachowaj błędy jako UNKNOWN."""
    root = Path(root)
    if root.is_symlink():
        raise ValueError("Katalog źródłowy nie może być dowiązaniem symbolicznym.")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Wymagany katalog źródłowy.")
    if max_files < 1:
        raise ValueError("Limit plików musi być dodatni.")
    excluded = []
    for value in exclude_paths:
        path = Path(value)
        if (path.is_absolute() or not path.parts or any(part in (".", "..") for part in path.parts)
                or ":" in str(path)):
            raise ValueError("Wykluczenia muszą być względnymi ścieżkami podfolderów.")
        excluded.append(path.as_posix())
    excluded = tuple(sorted(set(excluded)))
    rows = []
    errors = []
    if previous is not None and previous.get("root") != str(root):
        raise ValueError("Poprzednia migawka dotyczy innego katalogu.")
    prior = {row["path"]: row for row in previous.get("files", [])} if previous else {}
    pending = [root]
    while pending:
        if cancel_event is not None and cancel_event.is_set():
            errors.append({"path": ".", "error": "Skan przerwany przez użytkownika."})
            break
        folder = pending.pop()
        try:
            with os.scandir(folder) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except OSError as error:
            errors.append({"path": str(folder.relative_to(root)), "error": str(error)})
            continue
        for entry in entries:
            if cancel_event is not None and cancel_event.is_set():
                errors.append({"path": ".", "error": "Skan przerwany przez użytkownika."})
                pending.clear()
                break
            relative = str(Path(entry.path).relative_to(root))
            normalized = Path(relative).as_posix()
            if any(normalized == prefix or normalized.startswith(prefix + "/") for prefix in excluded):
                continue
            try:
                if entry.is_symlink():
                    errors.append({"path": relative, "error": "Pominięto dowiązanie symboliczne."})
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    if len(rows) >= max_files:
                        errors.append({"path": relative, "error": "Osiągnięto limit plików."})
                        pending.clear()
                        break
                    # DirEntry.stat().st_ino bywa zerowe na Windows; Path.stat()
                    # odczytuje identyfikator pliku potrzebny do rozpoznania rename.
                    stat = Path(entry.path).stat(follow_symlinks=False)
                    old = prior.get(relative)
                    if (not force_rehash and old is not None and old.get("size") == stat.st_size
                            and old.get("mtime_ns") == stat.st_mtime_ns):
                        digest = old["sha256"]
                    else:
                        digest = FileHashService.sha256(entry.path)
                    rows.append({"path": relative, "sha256": digest,
                                 "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                                 "inode": stat.st_ino})
            except (OSError, ValueError) as error:
                errors.append({"path": relative, "error": str(error)})
    if extended and rows:
        try:
            metadata = collect_extended(root, (row["path"] for row in rows))
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            metadata = {}
            errors.append({"path": ".", "error": f"ACL/ADS: {error}"})
        for row in rows:
            row["extended"] = metadata.get(row["path"],
                                           {"acl_status": "UNKNOWN", "ads_status": "UNKNOWN"})
            if not metadata_complete(row["extended"]):
                errors.append({"path": row["path"], "error": "Niepełny odczyt ACL/ADS."})
    return {
        "schema_version": 1,
        "root": str(root),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": sorted(rows, key=lambda row: row["path"]),
        "errors": sorted(errors, key=lambda row: row["path"]),
        "complete": not errors,
        "options": {"extended": extended, "exclude_paths": list(excluded)},
    }


def compare_files(earlier, later):
    if earlier.get("schema_version") != 1 or later.get("schema_version") != 1:
        raise ValueError("Nieobsługiwana migawka plików.")
    if earlier.get("root") != later.get("root"):
        raise ValueError("Migawki dotyczą różnych katalogów.")
    before = {row["path"]: row["sha256"] for row in earlier["files"]}
    after = {row["path"]: row["sha256"] for row in later["files"]}
    if not earlier.get("complete") or not later.get("complete"):
        return {"status": "UNKNOWN", "reason": "Co najmniej jedna migawka jest niepełna."}
    before_extended = earlier.get("options", {}).get("extended", False)
    after_extended = later.get("options", {}).get("extended", False)
    if before_extended != after_extended:
        return {"status": "UNKNOWN", "reason": "Migawki mają różne tryby ACL/ADS."}
    if earlier.get("options", {}).get("exclude_paths", []) != later.get("options", {}).get("exclude_paths", []):
        return {"status": "UNKNOWN", "reason": "Migawki mają różne wykluczenia podfolderów."}
    if before_extended:
        if any(not metadata_complete(row.get("extended"))
               for row in earlier["files"] + later["files"]):
            return {"status": "UNKNOWN", "reason": "Metadane ACL/ADS są niepełne."}
        full_before = {row["path"]: row.get("extended") for row in earlier["files"]}
        full_after = {row["path"]: row.get("extended") for row in later["files"]}
    else:
        full_before = full_after = {}
    return {
        "status": "COMPLETE",
        "added": sorted(after.keys() - before.keys()),
        "removed": sorted(before.keys() - after.keys()),
        "changed": sorted(path for path in before.keys() & after.keys()
                          if before[path] != after[path]
                          or (before_extended and full_before[path] != full_after[path])),
    }


def classify_file_events(earlier, later):
    """Rozpoznaj jednoznaczne zmiany nazwy bez zmiany treści pliku."""
    result = compare_files(earlier, later)
    if result["status"] != "COMPLETE":
        return result
    before = {row["path"]: row for row in earlier["files"]}
    after = {row["path"]: row for row in later["files"]}
    metadata_changed = {path for path in before.keys() & after.keys()
                        if before[path].get("mtime_ns") != after[path].get("mtime_ns")}
    result["changed"] = sorted(set(result["changed"]) | metadata_changed)
    added = set(result["added"])
    removed = set(result["removed"])
    renamed = []
    for old_path in sorted(removed):
        old = before[old_path]
        inode = old.get("inode")
        if not inode:
            continue
        matches = [new_path for new_path in added
                   if after[new_path].get("inode") == inode
                   and after[new_path]["sha256"] == old["sha256"]]
        old_matches = [path for path in removed
                       if before[path].get("inode") == inode
                       and before[path]["sha256"] == old["sha256"]]
        if len(matches) == 1 and len(old_matches) == 1:
            new_path = matches[0]
            renamed.append({"old_path": old_path, "path": new_path})
            removed.remove(old_path)
            added.remove(new_path)
    result["added"] = sorted(added)
    result["removed"] = sorted(removed)
    result["renamed"] = renamed
    return result
