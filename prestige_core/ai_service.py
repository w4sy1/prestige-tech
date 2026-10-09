"""Wspólna analiza raportów Centrów; sieć tylko po jawnym wywołaniu external()."""

import hashlib
from pathlib import Path

from .ai_normalization import normalize
from .ai_providers import LocalProvider
from .ai_remote import analyze as remote_analyze, payload
from .security_check import load_evidence


def metrics_from_file(path):
    return normalize(load_evidence(path))


def local(path):
    return LocalProvider().analyze(metrics_from_file(path))


def local_many(paths):
    """Połącz 2–10 zapisanych raportów do lokalnej oceny, bez twierdzeń przyczynowych."""
    if not isinstance(paths, (list, tuple)) or not 2 <= len(paths) <= 10:
        raise ValueError("Wybierz 2–10 raportów JSON.")
    if len({str(Path(path).resolve()).casefold() for path in paths}) != len(paths):
        raise ValueError("Każdy raport musi być innym plikiem.")
    documents = []
    sources = []
    for path in paths:
        if Path(path).stat().st_size > 64 * 1024 * 1024:
            raise ValueError("Raport przekracza 64 MiB.")
        documents.append(load_evidence(path))
        with Path(path).open("rb") as stream:
            sources.append(hashlib.file_digest(stream, "sha256").hexdigest())
    result = LocalProvider().analyze(normalize({"reports": documents}))
    result["source_count"] = len(paths)
    result["source_sha256"] = sources
    result["note"] += " Zbieżność metryk z wielu raportów nie potwierdza przyczyny problemu."
    return result


def preview(path, model):
    metrics = metrics_from_file(path)
    return {"data_leaves_device": False, "preview": payload(metrics, model),
            "note": "To jest dokładne żądanie do API; podgląd niczego nie wysyła."}


def external(path, model, *, expected_payload=None, analyzer=remote_analyze):
    metrics = metrics_from_file(path)
    if expected_payload is not None and payload(metrics, model) != expected_payload:
        raise ValueError("Raport lub model zmienił się od podglądu. Obejrzyj dane ponownie.")
    return analyzer(metrics, model)
