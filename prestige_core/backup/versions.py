"""Lista lokalnych wersji kopii bez otwierania ich zawartości."""

from datetime import datetime, timezone
from pathlib import Path

from .backup import load_manifest


def list_versions(parent, *, limit=50):
    root = Path(parent).resolve(strict=True)
    if not root.is_dir() or not 1 <= limit <= 100:
        raise ValueError("Wybierz katalog kopii i prawidłowy limit.")
    versions = []
    unreadable = 0
    for folder in root.iterdir():
        if not folder.is_dir() or folder.is_symlink():
            continue
        manifest = folder / "manifest.json"
        if not manifest.is_file() or manifest.is_symlink():
            continue
        try:
            if manifest.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("Manifest zbyt duży")
            data = load_manifest(folder)
            timestamp = datetime.fromtimestamp(manifest.stat().st_mtime, tz=timezone.utc).isoformat()
            versions.append({"name": folder.name, "path": str(folder),
                             "modified_utc": timestamp, "file_count": len(data["files"]),
                             "complete": data["complete"] and not data["errors"],
                             "integrity_checked": False})
        except (OSError, ValueError, KeyError, TypeError):
            unreadable += 1
    versions.sort(key=lambda row: row["modified_utc"], reverse=True)
    return {"versions": versions[:limit], "total_found": len(versions),
            "unreadable": unreadable, "note": "Lista nie sprawdza sum plików. Przed odtworzeniem użyj «Sprawdź kopię»."}
