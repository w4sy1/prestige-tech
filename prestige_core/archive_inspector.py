"""Odczyt metadanych ZIP/TAR bez rozpakowywania ani uruchamiania plików."""

from pathlib import Path, PurePosixPath
import tarfile
import zipfile


EXECUTABLE_SUFFIXES = {".exe", ".dll", ".scr", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jar", ".msi"}
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
MAX_ENTRIES = 10000


def _flags(name, *, size, compressed, link=False, encrypted=False):
    normalized = name.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    flags = []
    if (normalized.startswith(("/", "//")) or len(normalized) > 1 and normalized[1] == ":"
            or ".." in parts):
        flags.append("PATH_ESCAPE")
    if link:
        flags.append("LINK")
    if encrypted:
        flags.append("ENCRYPTED")
    suffix = PurePosixPath(normalized).suffix.lower()
    if suffix in EXECUTABLE_SUFFIXES:
        flags.append("EXECUTABLE_NAME")
    if compressed is not None and size > 100 * 1024 * 1024 and size > max(compressed, 1) * 100:
        flags.append("HIGH_EXPANSION_RATIO")
    return flags


def inspect_archive(path):
    source = Path(path)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Wymagane zwykłe archiwum do 2 GiB.")
    rows = []
    total = 0
    truncated = False
    try:
        if zipfile.is_zipfile(source):
            kind = "ZIP"
            with zipfile.ZipFile(source) as archive:
                for index, item in enumerate(archive.infolist()):
                    if index >= MAX_ENTRIES:
                        truncated = True
                        break
                    if item.is_dir():
                        continue
                    link = ((item.external_attr >> 16) & 0o170000) == 0o120000
                    rows.append({"name": item.filename[:500], "size": item.file_size,
                                 "compressed": item.compress_size,
                                 "flags": _flags(item.filename, size=item.file_size,
                                                 compressed=item.compress_size, link=link,
                                                 encrypted=bool(item.flag_bits & 1))})
                    total += item.file_size
        elif tarfile.is_tarfile(source):
            kind = "TAR"
            with tarfile.open(source, mode="r:*") as archive:
                for index, item in enumerate(archive):
                    if index >= MAX_ENTRIES:
                        truncated = True
                        break
                    if item.isdir():
                        continue
                    size = max(item.size, 0)
                    rows.append({"name": item.name[:500], "size": size, "compressed": None,
                                 "flags": _flags(item.name, size=size, compressed=None,
                                                 link=item.issym() or item.islnk())})
                    total += size
        else:
            raise ValueError("Obsługiwane są tylko ZIP i TAR (także skompresowany TAR).")
    except (zipfile.BadZipFile, tarfile.TarError, EOFError, OSError) as error:
        raise ValueError("Nie udało się odczytać metadanych archiwum.") from error
    return {"schema_version": 1, "kind": kind, "archive_size": source.stat().st_size,
            "entries_shown": len(rows), "total_unpacked_bytes_declared": total,
            "truncated": truncated, "entries": rows,
            "note": "Tylko metadane; bez ekstrakcji i analizy treści. Rozmiary w nagłówkach mogą być fałszywe."}
