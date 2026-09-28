"""Bezpieczny import baseline starego Integrity Monitor do Monitora."""

from pathlib import Path, PurePosixPath
import os
import re

from .file_extended import metadata_complete


_HASH = re.compile(r"[0-9a-fA-F]{64}\Z")


def convert_baseline(data):
    if (not isinstance(data, dict) or data.get("schema_version") != 1
            or not isinstance(data.get("root"), str)
            or not isinstance(data.get("files"), dict)
            or not isinstance(data.get("options"), dict)
            or type(data.get("options", {}).get("extended")) is not bool
            or type(data.get("ok")) is not bool):
        raise ValueError("Nieprawidłowy baseline starego Integrity Monitor.")
    root = Path(data["root"])
    if not root.is_absolute():
        raise ValueError("Baseline nie ma bezwzględnego katalogu źródłowego.")
    extended = data["options"]["extended"]
    rows, errors, seen = [], [], set()
    for name, old in data["files"].items():
        if not isinstance(name, str) or "\\" in name:
            raise ValueError("Nieprawidłowa ścieżka w baseline.")
        relative = PurePosixPath(name)
        if (relative.is_absolute() or not relative.parts or ":" in relative.parts[0]
                or any(part in {".", ".."} for part in relative.parts)
                or not isinstance(old, dict)
                or type(old.get("size")) is not int or old["size"] < 0
                or type(old.get("mtime_ns")) is not int or old["mtime_ns"] < 0
                or not isinstance(old.get("sha256"), str)
                or not _HASH.fullmatch(old["sha256"])):
            raise ValueError("Nieprawidłowy wpis starego baseline.")
        normalized = os.sep.join(relative.parts)
        if normalized.casefold() in seen:
            raise ValueError("Powtórzona ścieżka w baseline.")
        seen.add(normalized.casefold())
        row = {"path": normalized, "size": old["size"],
               "mtime_ns": old["mtime_ns"], "sha256": old["sha256"]}
        if extended:
            row["extended"] = old.get("extended")
            if not metadata_complete(row["extended"]):
                errors.append({"path": normalized, "error": "Niepełne ACL/ADS w starym baseline."})
        rows.append(row)
    if data.get("incomplete_files"):
        errors.append({"path": ".", "error": "Stary baseline oznaczony jako niepełny."})
    if not data["ok"]:
        errors.append({"path": ".", "error": "Stary baseline oznaczony jako niepoprawny."})
    return {"schema_version": 1, "root": str(root),
            "captured_at_utc": data.get("created_utc"),
            "files": sorted(rows, key=lambda row: row["path"]),
            "errors": errors, "complete": not errors,
            "options": {"extended": extended}, "imported_from": "Integrity Monitor v1"}
