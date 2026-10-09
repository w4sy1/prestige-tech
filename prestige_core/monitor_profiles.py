"""Profile ręcznego i pollingowego skanu Monitora."""

import json
from pathlib import Path


def validate_profile(data):
    if (not isinstance(data, dict) or data.get("schema_version") != 1
            or not isinstance(data.get("root"), str)
            or type(data.get("extended")) is not bool
            or not isinstance(data.get("exclude_paths"), list)):
        raise ValueError("Nieprawidłowy profil Monitora.")
    root = Path(data["root"])
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Katalog profilu nie istnieje.")
    excludes = []
    for value in data["exclude_paths"]:
        if not isinstance(value, str):
            raise ValueError("Nieprawidłowe wykluczenie.")
        relative = Path(value)
        if (relative.is_absolute() or not relative.parts or any(part in (".", "..") for part in relative.parts)
                or ":" in value or not (root / relative).is_dir()
                or (root / relative).is_symlink()
                or not (root / relative).resolve().is_relative_to(root.resolve())):
            raise ValueError("Wykluczenie musi być istniejącym podfolderem katalogu źródłowego.")
        excludes.append(relative.as_posix())
    return {"schema_version": 1, "root": str(root.resolve()),
            "extended": data["extended"], "exclude_paths": sorted(set(excludes))}


def save_profile(data, destination):
    profile = validate_profile(data)
    path = Path(destination)
    if path.resolve().is_relative_to(Path(profile["root"])):
        raise ValueError("Profil musi być zapisany poza obserwowanym katalogiem.")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(profile, stream, ensure_ascii=False, indent=2)
    return str(path)


def load_profile(source):
    path = Path(source)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Profil jest zbyt duży.")
    return validate_profile(json.loads(path.read_text(encoding="utf-8-sig")))
